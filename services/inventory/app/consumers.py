"""Inventory Service — Kafka Consumers.

Handles stock reservation on OrderCreatedEvent and stock release on
PaymentFailedEvent/OrderCancelledEvent. Uses inbox for exactly-once processing
and transactional outbox for response events.
"""
import asyncio
import uuid
from typing import Any

import structlog
from app.config import settings
from app.locking import acquire_lock
from app.models import InboxMessage, Inventory, OutboxMessage
from cloudscale_shared.database import db_manager, redis_manager
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

    # Start outbox worker
    outbox_worker = OutboxWorker(
        sessionmaker=db_manager._sessionmaker,
        outbox_model=OutboxMessage,
        producer=producer,
        poll_interval_seconds=0.5,
    )
    await outbox_worker.start()

    # Consumes from order-events and payment-events
    consumer = KafkaConsumerWrapper(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id="inventory-service-group",
        topics=[settings.ORDER_EVENTS_TOPIC, settings.PAYMENT_EVENTS_TOPIC],
    )
    await consumer.start()

    asyncio.create_task(consumer.consume_loop(handle_event))
    logger.info("Inventory Kafka event consumer loop started.")


async def shutdown_kafka():
    if outbox_worker:
        await outbox_worker.stop()
    if consumer:
        await consumer.stop()
    if producer:
        await producer.stop()
    logger.info("Inventory Kafka producers and consumers closed.")


async def handle_event(event: dict[str, Any]):
    event_type = event.get("event_type")
    event_id = event.get("event_id", str(uuid.uuid4()))
    correlation_id = event.get("correlation_id", "unknown")
    payload = event.get("payload", {})

    logger.info(
        "Inventory consumer received event",
        event_type=event_type,
        event_id=event_id,
        correlation_id=correlation_id,
    )

    async with db_manager.session() as db:
        # Inbox deduplication
        if await inbox_already_processed(db, InboxMessage, event_id):
            return

        if event_type == "OrderCreatedEvent":
            await _handle_order_created(db, payload, correlation_id)
        elif event_type in ("PaymentFailedEvent", "OrderCancelledEvent"):
            await _handle_release_stock(db, payload, correlation_id)
        else:
            logger.info("Ignored event type in inventory service", event_type=event_type)
            return

        # Record to inbox
        record_inbox(db, InboxMessage, event_id, event_type, "inventory-consumer")


async def _handle_order_created(db, payload: dict[str, Any], correlation_id: str):
    """Reserve stock for each item. Write success/fail event to outbox."""
    order_id = payload.get("order_id")
    items = payload.get("items", [])

    logger.info("Processing stock reservation", order_id=order_id, items_count=len(items))

    reserved_items: list[tuple[str, int]] = []
    failed = False
    failure_reason = ""

    redis_client = redis_manager.get_client()
    try:
        for item in items:
            product_id = item.get("product_id")
            product_uuid = uuid.UUID(product_id)
            quantity = item.get("quantity", 0)
            lock_key = f"inventory:lock:{product_uuid}"

            async with acquire_lock(redis_client, lock_key):
                result = await db.execute(
                    select(Inventory).where(Inventory.product_id == product_uuid)
                )
                inventory = result.scalar_one_or_none()

                if not inventory or inventory.available_stock < quantity:
                    failed = True
                    failure_reason = f"Out of stock on item {product_id}"
                    logger.warn(
                        "Stock reservation failed",
                        product_id=product_id,
                        required=quantity,
                        available=inventory.available_stock if inventory else 0,
                    )
                    break

                # Deduct and reserve
                inventory.available_stock -= quantity
                inventory.reserved_stock += quantity
                inventory.version += 1
                reserved_items.append((product_id, quantity))

        if failed:
            # Rollback reserved items in-memory within same transaction
            for pid, qty in reserved_items:
                lock_key = f"inventory:lock:{pid}"
                async with acquire_lock(redis_client, lock_key):
                    result = await db.execute(
                        select(Inventory).where(Inventory.product_id == pid)
                    )
                    inv = result.scalar_one_or_none()
                    if inv:
                        inv.available_stock += qty
                        inv.reserved_stock -= qty
                        inv.version += 1

            # Write failure event to outbox
            fail_event = Event(
                event_type="InventoryReserveFailedEvent",
                correlation_id=correlation_id,
                payload={"order_id": order_id, "reason": failure_reason},
            )
            write_outbox(
                db, OutboxMessage, settings.INVENTORY_EVENTS_TOPIC, fail_event, key=order_id
            )
        else:
            # Write success event to outbox
            success_event = Event(
                event_type="InventoryReservedEvent",
                correlation_id=correlation_id,
                payload={"order_id": order_id, "items": items},
            )
            write_outbox(
                db, OutboxMessage, settings.INVENTORY_EVENTS_TOPIC, success_event, key=order_id
            )
            logger.info("Stock reserved successfully", order_id=order_id)

    finally:
        await redis_client.aclose()


async def _handle_release_stock(db, payload: dict[str, Any], correlation_id: str):
    """Release reserved stock back to available pool (compensation transaction)."""
    order_id = payload.get("order_id")
    items = payload.get("items", [])

    logger.info("Releasing reserved stock", order_id=order_id, items_count=len(items))

    redis_client = redis_manager.get_client()
    try:
        for item in items:
            product_id = item.get("product_id")
            product_uuid = uuid.UUID(product_id)
            quantity = item.get("quantity", 0)
            lock_key = f"inventory:lock:{product_uuid}"

            async with acquire_lock(redis_client, lock_key):
                result = await db.execute(
                    select(Inventory).where(Inventory.product_id == product_uuid)
                )
                inventory = result.scalar_one_or_none()

                if inventory:
                    release_qty = min(inventory.reserved_stock, quantity)
                    inventory.reserved_stock -= release_qty
                    inventory.available_stock += release_qty
                    inventory.version += 1
                    logger.info("Released stock", product_id=product_id, qty=release_qty)

        # Write release confirmation to outbox
        release_event = Event(
            event_type="InventoryReleasedEvent",
            correlation_id=correlation_id,
            payload={"order_id": order_id},
        )
        write_outbox(
            db, OutboxMessage, settings.INVENTORY_EVENTS_TOPIC, release_event, key=order_id
        )
        logger.info("Stock released successfully", order_id=order_id)

    except Exception as e:
        logger.error("Failed to release stock", order_id=order_id, error=str(e))
    finally:
        await redis_client.aclose()
