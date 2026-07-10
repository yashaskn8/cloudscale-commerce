"""Order Service — Kafka Consumers (Saga State Machine).

Consumes events from inventory-events and payment-events topics to drive the
Order Saga through its state machine transitions. Uses inbox deduplication for
exactly-once processing and transactional outbox for compensation events.

Saga State Machine:
    PENDING ──[InventoryReservedEvent]──► STOCK_RESERVED
    STOCK_RESERVED ──[PaymentSuccessEvent]──► CONFIRMED
    PENDING/STOCK_RESERVED ──[InventoryReserveFailedEvent]──► CANCELLED_NO_STOCK
    PENDING/STOCK_RESERVED ──[PaymentFailedEvent]──► CANCELLED
                                                      └──► emit OrderCancelledEvent (compensation)
"""
import asyncio
import uuid
from typing import Any

import structlog
from app.config import settings
from app.models import InboxMessage, Order, OrderStatus, OutboxMessage
from cloudscale_shared.database import db_manager
from cloudscale_shared.events import Event, KafkaConsumerWrapper, KafkaProducerWrapper
from cloudscale_shared.inbox import inbox_already_processed, record_inbox
from cloudscale_shared.outbox import OutboxWorker, write_outbox
from sqlalchemy import select

logger = structlog.get_logger()
producer: KafkaProducerWrapper | None = None
consumer: KafkaConsumerWrapper | None = None
outbox_worker: OutboxWorker | None = None


async def init_kafka():
    global producer, consumer, outbox_worker
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
    logger.info("Order Saga consumer loop started.")


async def shutdown_kafka():
    if outbox_worker:
        await outbox_worker.stop()
    if consumer:
        await consumer.stop()
    if producer:
        await producer.stop()
    logger.info("Order Kafka producers and consumers closed.")


async def handle_event(event: dict[str, Any]):
    event_type = event.get("event_type")
    event_id = event.get("event_id", str(uuid.uuid4()))
    correlation_id = event.get("correlation_id", "unknown")
    payload = event.get("payload", {})

    logger.info(
        "Order Saga received event",
        event_type=event_type,
        event_id=event_id,
        correlation_id=correlation_id,
    )

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
    result = await db.execute(
        select(Order).where(Order.id == uuid.UUID(order_id))
    )
    order = result.scalar_one_or_none()
    if order and order.status == OrderStatus.PENDING.value:
        order.status = OrderStatus.STOCK_RESERVED.value
        logger.info("Order transitioned to STOCK_RESERVED", order_id=order_id)


async def _handle_inventory_reserve_failed(db, payload: dict, correlation_id: str):
    """Transition: PENDING → CANCELLED_NO_STOCK."""
    order_id = payload.get("order_id")
    result = await db.execute(
        select(Order).where(Order.id == uuid.UUID(order_id))
    )
    order = result.scalar_one_or_none()
    if order and order.status in (OrderStatus.PENDING.value, OrderStatus.STOCK_RESERVED.value):
        order.status = OrderStatus.CANCELLED_NO_STOCK.value
        logger.warn(
            "Order cancelled — no stock",
            order_id=order_id,
            reason=payload.get("reason"),
        )


async def _handle_payment_success(db, payload: dict, correlation_id: str):
    """Transition: STOCK_RESERVED → CONFIRMED."""
    order_id = payload.get("order_id")
    result = await db.execute(
        select(Order).where(Order.id == uuid.UUID(order_id))
    )
    order = result.scalar_one_or_none()
    if order and order.status == OrderStatus.STOCK_RESERVED.value:
        order.status = OrderStatus.CONFIRMED.value
        logger.info("Order CONFIRMED", order_id=order_id)


async def _handle_payment_failed(db, payload: dict, correlation_id: str):
    """Transition: STOCK_RESERVED → CANCELLED, emit OrderCancelledEvent for compensation."""
    order_id = payload.get("order_id")
    result = await db.execute(
        select(Order).where(Order.id == uuid.UUID(order_id))
    )
    order = result.scalar_one_or_none()
    if not order or order.status not in (
        OrderStatus.PENDING.value,
        OrderStatus.STOCK_RESERVED.value,
    ):
        return

    order.status = OrderStatus.CANCELLED.value

    # Build compensation event with item details for inventory release
    items_to_release = [
        {"product_id": str(i.product_id), "quantity": i.quantity}
        for i in order.items
    ]

    cancel_event = Event(
        event_type="OrderCancelledEvent",
        correlation_id=correlation_id,
        payload={"order_id": order_id, "items": items_to_release},
    )

    # Write compensation event to outbox (same transaction as status change)
    write_outbox(
        db, OutboxMessage, settings.ORDER_EVENTS_TOPIC, cancel_event, key=order_id
    )

    logger.info(
        "Order CANCELLED — compensation event written to outbox",
        order_id=order_id,
    )
