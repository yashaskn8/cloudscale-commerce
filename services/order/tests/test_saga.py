import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from app.consumers import handle_event
from app.models import OrderStatus, OutboxMessage
from app.schemas import OrderCreate, OrderItemCreate
from app.service import OrderService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_successful_saga_checkout(db_session: AsyncSession, monkeypatch):
    # Mock Kafka producer wrapper
    mock_producer = AsyncMock()
    monkeypatch.setattr("app.consumers.producer", mock_producer)

    service = OrderService(db_session)
    user_id = uuid.uuid4()
    item_id = uuid.uuid4()
    idempotency_key = "idem-test-saga-success-001"

    # 1. Create order
    payload = OrderCreate(
        items=[OrderItemCreate(product_id=item_id, quantity=2, unit_price=Decimal("10.00"))],
        idempotency_key=idempotency_key
    )
    order = await service.create_order(user_id, payload)
    assert order.status == OrderStatus.PENDING.value
    await db_session.commit()

    # Verify event is in outbox
    outbox_stmt = select(OutboxMessage).where(OutboxMessage.processed == False)
    outbox_res = await db_session.execute(outbox_stmt)
    outbox_msgs = outbox_res.scalars().all()
    assert len(outbox_msgs) == 1
    assert outbox_msgs[0].event_type == "OrderCreatedEvent"
    correlation_id = outbox_msgs[0].correlation_id

    # 2. Simulate Inventory Service reserving stock
    event_id = str(uuid.uuid4())
    inventory_reserved_event = {
        "event_id": event_id,
        "event_type": "InventoryReservedEvent",
        "correlation_id": correlation_id,
        "payload": {
            "order_id": str(order.id),
            "items": [{"product_id": str(item_id), "quantity": 2}]
        }
    }
    await handle_event(inventory_reserved_event)

    # Correct async refresh of order state
    await db_session.refresh(order)
    assert order.status == OrderStatus.STOCK_RESERVED.value

    # 3. Simulate Payment Service processing payment successfully
    payment_success_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "PaymentSuccessEvent",
        "correlation_id": correlation_id,
        "payload": {
            "order_id": str(order.id),
            "transaction_id": "txn_test_12345"
        }
    }
    await handle_event(payment_success_event)

    # Correct async refresh
    await db_session.refresh(order)
    assert order.status == OrderStatus.CONFIRMED.value


@pytest.mark.asyncio
async def test_failed_payment_triggers_compensation(db_session: AsyncSession, monkeypatch):
    # Mock Kafka producer wrapper
    mock_producer = AsyncMock()
    monkeypatch.setattr("app.consumers.producer", mock_producer)

    service = OrderService(db_session)
    user_id = uuid.uuid4()
    item_id = uuid.uuid4()
    idempotency_key = "idem-test-saga-payment-fail-001"

    # 1. Create order
    payload = OrderCreate(
        items=[OrderItemCreate(product_id=item_id, quantity=2, unit_price=Decimal("15.00"))],
        idempotency_key=idempotency_key
    )
    order = await service.create_order(user_id, payload)
    assert order.status == OrderStatus.PENDING.value

    # Simulate stock reservation transition
    order.status = OrderStatus.STOCK_RESERVED.value
    await db_session.commit()

    # 2. Simulate Payment Failure
    correlation_id = "corr-fail-99"
    payment_failed_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "PaymentFailedEvent",
        "correlation_id": correlation_id,
        "payload": {
            "order_id": str(order.id),
            "reason": "Card declined."
        }
    }
    await handle_event(payment_failed_event)

    # Correct async refresh
    await db_session.refresh(order)
    assert order.status == OrderStatus.CANCELLED.value

    # Verify compensating event OrderCancelledEvent was written to outbox
    outbox_stmt = select(OutboxMessage).where(OutboxMessage.event_type == "OrderCancelledEvent")
    outbox_res = await db_session.execute(outbox_stmt)
    outbox_msgs = outbox_res.scalars().all()
    assert len(outbox_msgs) == 1
    assert outbox_msgs[0].correlation_id == correlation_id


@pytest.mark.asyncio
async def test_inbox_deduplication(db_session: AsyncSession, monkeypatch):
    mock_producer = AsyncMock()
    monkeypatch.setattr("app.consumers.producer", mock_producer)

    service = OrderService(db_session)
    user_id = uuid.uuid4()
    item_id = uuid.uuid4()
    idempotency_key = "idem-test-inbox-dedup"

    payload = OrderCreate(
        items=[OrderItemCreate(product_id=item_id, quantity=1, unit_price=Decimal("5.00"))],
        idempotency_key=idempotency_key
    )
    order = await service.create_order(user_id, payload)
    await db_session.commit()

    # Deliver the same InventoryReservedEvent twice with identical event_id
    event_id = str(uuid.uuid4())
    inventory_reserved_event = {
        "event_id": event_id,
        "event_type": "InventoryReservedEvent",
        "correlation_id": "corr-dedup-1",
        "payload": {
            "order_id": str(order.id),
            "items": [{"product_id": str(item_id), "quantity": 1}]
        }
    }

    # First delivery
    await handle_event(inventory_reserved_event)

    # Correct async refresh
    await db_session.refresh(order)
    assert order.status == OrderStatus.STOCK_RESERVED.value

    # Force change status back to PENDING directly in database to check if second delivery is ignored
    order.status = OrderStatus.PENDING.value
    await db_session.commit()

    # Second delivery (identical event_id)
    await handle_event(inventory_reserved_event)

    # Correct async refresh
    await db_session.refresh(order)
    assert order.status == OrderStatus.PENDING.value
