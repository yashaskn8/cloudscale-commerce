"""Order Service — Kafka Consumers & Saga State Machine.

Consumes events from inventory-events and payment-events topics to drive the
Order Saga through its state machine transitions. Uses inbox deduplication for
exactly-once processing and transactional outbox for compensation events.

Saga State Machine:
    PENDING ──[InventoryReservedEvent]──► STOCK_RESERVED
    STOCK_RESERVED ──[PaymentSuccessEvent]──► CONFIRMED
    PENDING/STOCK_RESERVED ──[InventoryReserveFailedEvent]──► CANCELLED_NO_STOCK
    PENDING/STOCK_RESERVED ──[PaymentFailedEvent]──► CANCELLED
                                                      └──► emit OrderCancelledEvent (compensation)
    PENDING/STOCK_RESERVED ──[Saga Timeout]──► CANCELLED
                                               └──► emit OrderCancelledEvent (compensation)
"""

import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from app.config import settings
from app.models import InboxMessage, Order, OrderStatus, OutboxMessage
from cloudscale_shared.database import db_manager
from cloudscale_shared.events import Event, KafkaConsumerWrapper, KafkaProducerWrapper
from cloudscale_shared.inbox import inbox_already_processed, record_inbox
from cloudscale_shared.outbox import OutboxWorker, write_outbox
from cloudscale_shared.resilience import CircuitBreaker, circuit_breaker, retry_with_backoff
from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import select

logger = structlog.get_logger()
producer: KafkaProducerWrapper | None = None
consumer: KafkaConsumerWrapper | None = None
outbox_worker: OutboxWorker | None = None
sweeper_task: asyncio.Task | None = None

# Circuit Breaker for Order DB Operations
order_db_breaker = CircuitBreaker("order_db_consumer")

# Prometheus Telemetry
SAGA_SWEEPS_TOTAL = Counter("saga_sweeps_total", "Total saga timeout sweep executions")
SAGA_TIMEOUT_TOTAL = Counter("saga_timeout_total", "Total stale orders timed out by sweeper")
STALE_ORDERS_FOUND = Gauge("stale_orders_found", "Current count of stale pending/reserved orders")
SAGA_SWEEP_DURATION = Histogram("saga_sweep_duration_seconds", "Duration of saga timeout sweep loop")
CONSUMER_PROCESSING_DURATION = Histogram(
    "order_consumer_processing_seconds", "Processing time for order events", ["event_type"]
)
CONSUMER_FAILURES = Counter("order_consumer_failures_total", "Failures processing order events", ["event_type"])


async def init_kafka():
    global producer, consumer, outbox_worker, sweeper_task
    producer = KafkaProducerWrapper(settings.KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()

    # Start outbox worker to publish events from outbox table
    outbox_worker = OutboxWorker(
        sessionmaker=db_manager._sessionmaker,
        outbox_model=OutboxMessage,
        producer=producer,
        poll_interval_seconds=0.5,
    )
    await outbox_worker.start()

    # Consume from inventory-events and payment-events to drive Saga
    consumer = KafkaConsumerWrapper(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="order-service-group",
        topics=[settings.INVENTORY_EVENTS_TOPIC, settings.PAYMENT_EVENTS_TOPIC],
    )
    await consumer.start()

    asyncio.create_task(consumer.consume_loop(handle_event))
    sweeper_task = asyncio.create_task(_saga_sweeper_loop())
    logger.info("Order Saga consumer loop and timeout sweeper started.")


async def shutdown_kafka():
    if sweeper_task:
        sweeper_task.cancel()
    if outbox_worker:
        await outbox_worker.stop()
    if consumer:
        await consumer.stop()
    if producer:
        await producer.stop()
    logger.info("Order Kafka producers, consumers, and sweeper closed.")


async def handle_event(event: dict[str, Any]):
    event_type = event.get("event_type", "unknown")
    event_id = event.get("event_id", str(uuid.uuid4()))
    correlation_id = event.get("correlation_id", "unknown")
    payload = event.get("payload", {})

    logger.info(
        "Order Saga received event",
        event_type=event_type,
        event_id=event_id,
        correlation_id=correlation_id,
    )

    start_time = time.perf_counter()
    try:
        await _process_event_with_resilience(event_type, event_id, correlation_id, payload)
        duration = time.perf_counter() - start_time
        CONSUMER_PROCESSING_DURATION.labels(event_type=event_type).observe(duration)
    except Exception as e:
        CONSUMER_FAILURES.labels(event_type=event_type).inc()
        logger.error("Error processing order saga event", event_type=event_type, error=str(e))
        raise


@circuit_breaker(order_db_breaker)
@retry_with_backoff("order_event_db_process", max_attempts=3)
async def _process_event_with_resilience(event_type: str, event_id: str, correlation_id: str, payload: dict):
    async with db_manager.session() as db:
        # Inbox deduplication check
        if await inbox_already_processed(db, InboxMessage, event_id):
            return

        if event_type == "InventoryReservedEvent":
            await _handle_inventory_reserved(db, payload, correlation_id)
        elif event_type == "InventoryReserveFailedEvent":
            await _handle_inventory_reserve_failed(db, payload, correlation_id)
        elif event_type == "PaymentSuccessEvent":
            await _handle_payment_success(db, payload, correlation_id)
        elif event_type == "PaymentFailedEvent":
            await _handle_payment_failed(db, payload, correlation_id)
        else:
            logger.info("Ignored event type in order Saga", event_type=event_type)
            return

        # Record in inbox to prevent reprocessing
        record_inbox(db, InboxMessage, event_id, event_type, "order-saga")


async def _handle_inventory_reserved(db, payload: dict, correlation_id: str):
    """Transition: PENDING → STOCK_RESERVED."""
    order_id = payload.get("order_id")
    result = await db.execute(select(Order).where(Order.id == uuid.UUID(order_id)))
    order = result.scalar_one_or_none()
    if order and order.status == OrderStatus.PENDING.value:
        prev_state = order.status
        order.status = OrderStatus.STOCK_RESERVED.value
        logger.info(
            "Saga transition: STOCK_RESERVED",
            order_id=order_id,
            tenant_id=getattr(order, "tenant_id", "default"),
            previous_state=prev_state,
            new_state=order.status,
            event_type="InventoryReservedEvent",
            correlation_id=correlation_id,
        )


async def _handle_inventory_reserve_failed(db, payload: dict, correlation_id: str):
    """Transition: PENDING → CANCELLED_NO_STOCK."""
    order_id = payload.get("order_id")
    result = await db.execute(select(Order).where(Order.id == uuid.UUID(order_id)))
    order = result.scalar_one_or_none()
    if order and order.status in (OrderStatus.PENDING.value, OrderStatus.STOCK_RESERVED.value):
        prev_state = order.status
        order.status = OrderStatus.CANCELLED_NO_STOCK.value
        logger.warn(
            "Saga transition: CANCELLED_NO_STOCK",
            order_id=order_id,
            tenant_id=getattr(order, "tenant_id", "default"),
            previous_state=prev_state,
            new_state=order.status,
            event_type="InventoryReserveFailedEvent",
            correlation_id=correlation_id,
            reason=payload.get("reason"),
        )


async def _handle_payment_success(db, payload: dict, correlation_id: str):
    """Transition: STOCK_RESERVED → CONFIRMED."""
    order_id = payload.get("order_id")
    result = await db.execute(select(Order).where(Order.id == uuid.UUID(order_id)))
    order = result.scalar_one_or_none()
    if order and order.status == OrderStatus.STOCK_RESERVED.value:
        prev_state = order.status
        order.status = OrderStatus.CONFIRMED.value
        logger.info(
            "Saga transition: CONFIRMED",
            order_id=order_id,
            tenant_id=getattr(order, "tenant_id", "default"),
            previous_state=prev_state,
            new_state=order.status,
            event_type="PaymentSuccessEvent",
            correlation_id=correlation_id,
        )


async def _handle_payment_failed(db, payload: dict, correlation_id: str):
    """Transition: STOCK_RESERVED → CANCELLED, emit OrderCancelledEvent for compensation."""
    order_id = payload.get("order_id")
    result = await db.execute(select(Order).where(Order.id == uuid.UUID(order_id)))
    order = result.scalar_one_or_none()
    if not order or order.status not in (
        OrderStatus.PENDING.value,
        OrderStatus.STOCK_RESERVED.value,
    ):
        return

    prev_state = order.status
    order.status = OrderStatus.CANCELLED.value

    # Build compensation event with item details for inventory release
    items_to_release = [{"product_id": str(i.product_id), "quantity": i.quantity} for i in order.items]

    cancel_event = Event(
        event_type="OrderCancelledEvent",
        correlation_id=correlation_id,
        payload={"order_id": order_id, "items": items_to_release},
    )

    # Write compensation event to outbox (same transaction as status change)
    write_outbox(db, OutboxMessage, settings.ORDER_EVENTS_TOPIC, cancel_event, key=order_id)

    logger.warn(
        "Saga transition: CANCELLED (Compensation triggered)",
        order_id=order_id,
        tenant_id=getattr(order, "tenant_id", "default"),
        previous_state=prev_state,
        new_state=order.status,
        event_type="PaymentFailedEvent",
        correlation_id=correlation_id,
    )


# ── Saga Timeout Sweeper Loop ──────────────────────────────────────────────────


async def _saga_sweeper_loop():
    """Periodic background worker sweeping stale orders past timeout."""
    while True:
        try:
            await asyncio.sleep(settings.SAGA_SWEEP_INTERVAL_SECONDS)
            await sweep_stale_sagas()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in saga sweeper loop", error=str(e))


async def sweep_stale_sagas(cutoff_minutes: int | None = None, batch_size: int | None = None) -> int:
    """Finds and cancels stale orders in PENDING or STOCK_RESERVED past timeout.

    Processes stale orders in configurable batches until none remain.
    Returns total number of stale orders timed out.
    """
    SAGA_SWEEPS_TOTAL.inc()
    start_time = time.perf_counter()
    timeout_mins = cutoff_minutes if cutoff_minutes is not None else settings.SAGA_TIMEOUT_MINUTES
    batch_limit = batch_size if batch_size is not None else settings.SAGA_SWEEP_BATCH_SIZE

    total_timed_out = 0

    while True:
        cutoff_time = datetime.now(UTC) - timedelta(minutes=timeout_mins)

        async with db_manager.session() as db:
            stmt = (
                select(Order)
                .where(
                    Order.status.in_([OrderStatus.PENDING.value, OrderStatus.STOCK_RESERVED.value]),
                    Order.created_at <= cutoff_time,
                )
                .limit(batch_limit)
            )
            result = await db.execute(stmt)
            stale_orders = list(result.scalars().all())

            if not stale_orders:
                break

            STALE_ORDERS_FOUND.set(len(stale_orders))

            for order in stale_orders:
                prev_state = order.status
                order.status = OrderStatus.CANCELLED.value

                # Build compensation event if stock was reserved
                items_to_release = [{"product_id": str(i.product_id), "quantity": i.quantity} for i in order.items]
                correlation_id = f"timeout-{uuid.uuid4().hex[:8]}"

                cancel_event = Event(
                    event_type="OrderCancelledEvent",
                    correlation_id=correlation_id,
                    payload={"order_id": str(order.id), "items": items_to_release, "reason": "Saga execution timeout"},
                )
                write_outbox(db, OutboxMessage, settings.ORDER_EVENTS_TOPIC, cancel_event, key=str(order.id))

                SAGA_TIMEOUT_TOTAL.inc()
                total_timed_out += 1

                logger.warn(
                    "Saga transition: CANCELLED (Timeout sweeper)",
                    order_id=str(order.id),
                    tenant_id=getattr(order, "tenant_id", "default"),
                    previous_state=prev_state,
                    new_state=order.status,
                    event_type="SagaTimeout",
                    correlation_id=correlation_id,
                )

    SAGA_SWEEP_DURATION.observe(time.perf_counter() - start_time)
    return total_timed_out
