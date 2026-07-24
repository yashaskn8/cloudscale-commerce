"""Payment Service — Kafka Consumers.

Consumes events from inventory-events, performs idempotent simulated payment charges,
records transactions, and writes responses to the transactional outbox.

Note: Real Stripe integration is not yet wired. The payment flow operates in
simulated mode controlled by the SIMULATE_PAYMENTS config flag. See _process_payment()
for the documented extension point where stripe.PaymentIntent.create would be called.
"""

import asyncio
import time
import uuid
from typing import Any

import structlog
from app.config import settings
from app.models import InboxMessage, OutboxMessage, Payment
from cloudscale_shared.database import db_manager
from cloudscale_shared.events import Event, KafkaConsumerWrapper, KafkaProducerWrapper
from cloudscale_shared.inbox import inbox_already_processed, record_inbox
from cloudscale_shared.outbox import OutboxWorker, write_outbox
from cloudscale_shared.resilience import CircuitBreaker, circuit_breaker, retry_with_backoff
from prometheus_client import Counter, Histogram

logger = structlog.get_logger()
producer: KafkaProducerWrapper | None = None
consumer: KafkaConsumerWrapper | None = None
outbox_worker: OutboxWorker | None = None

# Circuit Breaker for Payment DB Operations
payment_db_breaker = CircuitBreaker("payment_db_consumer")

# Prometheus Telemetry
PAYMENT_PROCESSING_DURATION = Histogram("payment_consumer_processing_seconds", "Processing time for payment events")
PAYMENT_CONSUMER_FAILURES = Counter("payment_consumer_failures_total", "Failures processing payment events")


async def init_kafka():
    global producer, consumer, outbox_worker
    producer = KafkaProducerWrapper(settings.KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()

    # Start outbox worker
    outbox_worker = OutboxWorker(
        sessionmaker=db_manager._sessionmaker,
        outbox_model=OutboxMessage,
        producer=producer,
        poll_interval_seconds=0.5,
    )
    await outbox_worker.start()

    # Consumes from inventory-events
    consumer = KafkaConsumerWrapper(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="payment-service-group",
        topics=[settings.INVENTORY_EVENTS_TOPIC],
    )
    await consumer.start()

    asyncio.create_task(consumer.consume_loop(handle_event))
    logger.info("Payment Kafka event consumer loop started.")


async def shutdown_kafka():
    if outbox_worker:
        await outbox_worker.stop()
    if consumer:
        await consumer.stop()
    if producer:
        await producer.stop()
    logger.info("Payment Kafka producers and consumers closed.")


async def handle_event(event: dict[str, Any]):
    event_type = event.get("event_type")
    event_id = event.get("event_id", str(uuid.uuid4()))
    correlation_id = event.get("correlation_id", "unknown")
    payload = event.get("payload", {})

    logger.info(
        "Payment consumer received event",
        event_type=event_type,
        event_id=event_id,
        correlation_id=correlation_id,
    )

    start_time = time.perf_counter()
    try:
        await _process_event_with_resilience(event_type, event_id, correlation_id, payload)
        PAYMENT_PROCESSING_DURATION.observe(time.perf_counter() - start_time)
    except Exception as e:
        PAYMENT_CONSUMER_FAILURES.inc()
        logger.error("Error processing payment event", event_type=event_type, error=str(e))
        raise


@circuit_breaker(payment_db_breaker)
@retry_with_backoff("payment_event_db_process", max_attempts=3)
async def _process_event_with_resilience(event_type: str | None, event_id: str, correlation_id: str, payload: dict):
    async with db_manager.session() as db:
        # Inbox deduplication
        if await inbox_already_processed(db, InboxMessage, event_id):
            return

        if event_type == "InventoryReservedEvent":
            await _process_payment(db, payload, correlation_id)
        else:
            logger.info("Ignored event type in payment service", event_type=event_type)
            return

        # Record to inbox
        record_inbox(db, InboxMessage, event_id, event_type or "unknown", "payment-consumer")


async def _process_payment(db, payload: dict[str, Any], correlation_id: str):
    """Charges user card via Stripe, or runs a simulated charge when SIMULATE_PAYMENTS=True."""
    order_id = payload.get("order_id")
    items = payload.get("items", [])

    # Calculate amount
    amount = sum(item.get("quantity", 0) * item.get("unit_price", 0.0) for item in items)

    if not settings.SIMULATE_PAYMENTS:
        # ── Real Stripe integration path (TODO: wire stripe.PaymentIntent.create) ──
        logger.error(
            "Real payment processing is not yet implemented. "
            "Set SIMULATE_PAYMENTS=True for development/staging.",
            order_id=order_id,
            amount=amount,
        )
        raise NotImplementedError(
            "Real Stripe payment processing is not yet wired. "
            "Set SIMULATE_PAYMENTS=True to use the mock payment flow."
        )

    # ── Simulated payment path ──────────────────────────────────────────────
    logger.info(
        "Processing SIMULATED card payment charge",
        order_id=order_id,
        amount=amount,
        simulated=True,
    )

    # Determine failure trigger via explicit simulate_failure flag only
    should_fail = payload.get("simulate_failure", False) or any(
        item.get("simulate_failure", False) for item in items
    )

    # Simulate processing delay
    await asyncio.sleep(0.1)

    if should_fail:
        logger.warn("Simulated card payment failed", order_id=order_id, correlation_id=correlation_id)
        failed_event = Event(
            event_type="PaymentFailedEvent",
            correlation_id=correlation_id,
            payload={"order_id": order_id, "items": items, "reason": "Card declined. Insufficient funds."},
        )
        write_outbox(db, OutboxMessage, settings.PAYMENT_EVENTS_TOPIC, failed_event, key=order_id)
    else:
        transaction_id = f"sim_txn_{uuid.uuid4().hex[:16]}"

        # Save payment record in DB
        payment = Payment(
            order_id=uuid.UUID(order_id), transaction_id=transaction_id, amount=amount, status="COMPLETED"
        )
        db.add(payment)

        logger.info("Simulated card payment completed successfully", order_id=order_id, txn_id=transaction_id)

        success_event = Event(
            event_type="PaymentSuccessEvent",
            correlation_id=correlation_id,
            payload={"order_id": order_id, "items": items, "transaction_id": transaction_id},
        )
        write_outbox(db, OutboxMessage, settings.PAYMENT_EVENTS_TOPIC, success_event, key=order_id)
