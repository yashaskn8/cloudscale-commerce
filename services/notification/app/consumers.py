"""Notification Service — Kafka Consumers.

Consumes events from payment-events, deduping messages with InboxMessage to
ensure exactly-once transactional email dispatching.
"""
import asyncio
import uuid
from typing import Any

import structlog
from app.config import settings
from app.models import InboxMessage
from cloudscale_shared.database import db_manager
from cloudscale_shared.events import KafkaConsumerWrapper
from cloudscale_shared.inbox import inbox_already_processed, record_inbox

logger = structlog.get_logger()
consumer: KafkaConsumerWrapper | None = None


async def init_kafka():
    global consumer
    consumer = KafkaConsumerWrapper(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="notification-service-group",
        topics=[settings.PAYMENT_EVENTS_TOPIC]
    )
    await consumer.start()

    asyncio.create_task(consumer.consume_loop(handle_event))
    logger.info("Notification Kafka event consumer loop started.")


async def shutdown_kafka():
    if consumer:
        await consumer.stop()
    logger.info("Notification Kafka consumer closed.")


async def handle_event(event: dict[str, Any]):
    event_type = event.get("event_type")
    event_id = event.get("event_id", str(uuid.uuid4()))
    correlation_id = event.get("correlation_id", "unknown")
    payload = event.get("payload", {})

    logger.info(
        "Notification consumer received event",
        event_type=event_type,
        event_id=event_id,
        correlation_id=correlation_id
    )

    async with db_manager.session() as db:
        # Inbox check for exactly-once processing
        if await inbox_already_processed(db, InboxMessage, event_id):
            return

        if event_type == "PaymentSuccessEvent":
            await send_order_confirmation(payload, correlation_id)
        else:
            logger.info("Ignored event type in notification service", event_type=event_type)
            return

        # Record to inbox
        record_inbox(db, InboxMessage, event_id, event_type, "notification-consumer")


async def send_order_confirmation(payload: dict[str, Any], correlation_id: str):
    """Simulates sending an email confirmation following successful payment receipt."""
    order_id = payload.get("order_id")
    transaction_id = payload.get("transaction_id", "unknown")

    logger.info(
        "Sending Transactional Email: Order Confirmation",
        order_id=order_id,
        transaction_id=transaction_id,
        correlation_id=correlation_id
    )

    # Simulate API communication delay
    await asyncio.sleep(0.3)

    logger.info("Order confirmation email successfully dispatched.", order_id=order_id)
