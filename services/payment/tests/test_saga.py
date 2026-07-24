import uuid
from decimal import Decimal

import pytest
from app.consumers import handle_event
from app.models import OutboxMessage, Payment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_payment_processing_success(db_session: AsyncSession, monkeypatch):
    # Mock producer
    from unittest.mock import AsyncMock

    mock_producer = AsyncMock()
    monkeypatch.setattr("app.consumers.producer", mock_producer)

    product_id = uuid.uuid4()
    order_id = uuid.uuid4()
    correlation_id = "test-corr-payment-success"

    # Simulate InventoryReservedEvent
    inventory_reserved_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "InventoryReservedEvent",
        "correlation_id": correlation_id,
        "payload": {
            "order_id": str(order_id),
            "items": [{"product_id": str(product_id), "quantity": 2, "unit_price": 49.99}],
        },
    }

    # Process
    await handle_event(inventory_reserved_event)

    # Verify payment record in DB
    payments_stmt = select(Payment).where(Payment.order_id == order_id)
    payments_res = await db_session.execute(payments_stmt)
    payments = payments_res.scalars().all()
    assert len(payments) == 1
    assert payments[0].amount == Decimal("99.98")
    assert payments[0].status == "COMPLETED"

    # Verify PaymentSuccessEvent in outbox
    outbox_stmt = select(OutboxMessage).where(OutboxMessage.event_type == "PaymentSuccessEvent")
    outbox_res = await db_session.execute(outbox_stmt)
    outbox_msgs = outbox_res.scalars().all()
    assert len(outbox_msgs) == 1
    assert outbox_msgs[0].correlation_id == correlation_id


@pytest.mark.asyncio
async def test_payment_processing_failure_rollback_path(db_session: AsyncSession, monkeypatch):
    # Mock producer
    from unittest.mock import AsyncMock

    mock_producer = AsyncMock()
    monkeypatch.setattr("app.consumers.producer", mock_producer)

    product_id = uuid.uuid4()
    order_id = uuid.uuid4()
    correlation_id = "test-corr-payment-fail"

    # Simulate InventoryReservedEvent with quantity = 99 (triggers mock decline)
    inventory_reserved_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "InventoryReservedEvent",
        "correlation_id": correlation_id,
        "payload": {
            "order_id": str(order_id),
            "items": [{"product_id": str(product_id), "quantity": 99, "unit_price": 1.00}],
        },
    }

    # Process
    await handle_event(inventory_reserved_event)

    # Verify no payment record in DB
    payments_stmt = select(Payment).where(Payment.order_id == order_id)
    payments_res = await db_session.execute(payments_stmt)
    payments = payments_res.scalars().all()
    assert len(payments) == 0

    # Verify PaymentFailedEvent in outbox
    outbox_stmt = select(OutboxMessage).where(OutboxMessage.event_type == "PaymentFailedEvent")
    outbox_res = await db_session.execute(outbox_stmt)
    outbox_msgs = outbox_res.scalars().all()
    assert len(outbox_msgs) == 1
    assert outbox_msgs[0].correlation_id == correlation_id
