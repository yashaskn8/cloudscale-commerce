import uuid

import pytest
from app.consumers import handle_event
from app.models import Inventory, OutboxMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_inventory_reserve_and_release(db_session: AsyncSession, monkeypatch):
    # Mock producer
    from unittest.mock import AsyncMock

    mock_producer = AsyncMock()
    monkeypatch.setattr("app.consumers.producer", mock_producer)

    product_id = uuid.uuid4()
    order_id = str(uuid.uuid4())
    correlation_id = "test-corr-inv-saga"

    # Setup initial inventory level
    inv = Inventory(product_id=product_id, available_stock=10, reserved_stock=0, version=1)
    db_session.add(inv)
    await db_session.commit()

    # 1. Simulate OrderCreatedEvent (Stock reservation command)
    order_created_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "OrderCreatedEvent",
        "correlation_id": correlation_id,
        "payload": {"order_id": order_id, "items": [{"product_id": str(product_id), "quantity": 3}]},
    }
    await handle_event(order_created_event)

    # Refresh inventory state
    await db_session.refresh(inv)
    assert inv.available_stock == 7
    assert inv.reserved_stock == 3

    # Verify InventoryReservedEvent is written to Outbox
    outbox_stmt = select(OutboxMessage).where(OutboxMessage.event_type == "InventoryReservedEvent")
    outbox_res = await db_session.execute(outbox_stmt)
    outbox_msgs = outbox_res.scalars().all()
    assert len(outbox_msgs) == 1
    assert outbox_msgs[0].correlation_id == correlation_id

    # 2. Simulate Payment Failed (Compensating Stock Release command)
    payment_failed_event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "PaymentFailedEvent",
        "correlation_id": correlation_id,
        "payload": {"order_id": order_id, "items": [{"product_id": str(product_id), "quantity": 3}]},
    }
    await handle_event(payment_failed_event)

    # Refresh inventory state
    await db_session.refresh(inv)
    assert inv.available_stock == 10
    assert inv.reserved_stock == 0

    # Verify InventoryReleasedEvent is written to Outbox
    outbox_release_stmt = select(OutboxMessage).where(OutboxMessage.event_type == "InventoryReleasedEvent")
    outbox_release_res = await db_session.execute(outbox_release_stmt)
    outbox_release_msgs = outbox_release_res.scalars().all()
    assert len(outbox_release_msgs) == 1
