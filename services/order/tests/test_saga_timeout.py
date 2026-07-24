"""Tests for the Saga Timeout Sweeper.

Validates that stale orders in PENDING or STOCK_RESERVED states are
correctly cancelled by the sweeper after exceeding the saga timeout,
and that compensation OrderCancelledEvents are written to the outbox.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.consumers import sweep_stale_sagas
from app.models import Order, OrderStatus, OutboxMessage
from sqlalchemy import select


def _make_order(*, status: str, created_at: datetime) -> Order:
    """Helper to build a valid Order with all NOT NULL fields populated."""
    return Order(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        tenant_id="test-tenant",
        status=status,
        total_amount=Decimal("100.00"),
        idempotency_key=f"idem-{uuid.uuid4().hex[:12]}",
        created_at=created_at,
    )


@pytest.mark.asyncio
async def test_stale_pending_order_is_cancelled(db_session):
    """Orders stuck in PENDING past timeout should be swept to CANCELLED."""
    old_time = datetime.now(UTC) - timedelta(minutes=30)
    order = _make_order(status=OrderStatus.PENDING.value, created_at=old_time)
    db_session.add(order)
    await db_session.commit()

    timed_out = await sweep_stale_sagas(cutoff_minutes=15, batch_size=10)

    assert timed_out == 1
    await db_session.refresh(order)
    assert order.status == OrderStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_stale_stock_reserved_order_is_cancelled(db_session):
    """Orders stuck in STOCK_RESERVED past timeout should be swept to CANCELLED."""
    old_time = datetime.now(UTC) - timedelta(minutes=30)
    order = _make_order(status=OrderStatus.STOCK_RESERVED.value, created_at=old_time)
    db_session.add(order)
    await db_session.commit()

    timed_out = await sweep_stale_sagas(cutoff_minutes=15, batch_size=10)

    assert timed_out == 1
    await db_session.refresh(order)
    assert order.status == OrderStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_recent_pending_order_not_swept(db_session):
    """Orders created within the timeout window should NOT be swept."""
    recent_time = datetime.now(UTC) - timedelta(minutes=5)
    order = _make_order(status=OrderStatus.PENDING.value, created_at=recent_time)
    db_session.add(order)
    await db_session.commit()

    timed_out = await sweep_stale_sagas(cutoff_minutes=15, batch_size=10)

    assert timed_out == 0
    await db_session.refresh(order)
    assert order.status == OrderStatus.PENDING.value


@pytest.mark.asyncio
async def test_confirmed_order_not_swept(db_session):
    """Orders in CONFIRMED state should never be touched by the sweeper."""
    old_time = datetime.now(UTC) - timedelta(minutes=60)
    order = _make_order(status=OrderStatus.CONFIRMED.value, created_at=old_time)
    db_session.add(order)
    await db_session.commit()

    timed_out = await sweep_stale_sagas(cutoff_minutes=15, batch_size=10)

    assert timed_out == 0
    await db_session.refresh(order)
    assert order.status == OrderStatus.CONFIRMED.value


@pytest.mark.asyncio
async def test_sweep_writes_compensation_event_to_outbox(db_session):
    """Sweeping a stale order should write an OrderCancelledEvent to outbox."""
    old_time = datetime.now(UTC) - timedelta(minutes=30)
    order = _make_order(status=OrderStatus.PENDING.value, created_at=old_time)
    db_session.add(order)
    await db_session.commit()

    await sweep_stale_sagas(cutoff_minutes=15, batch_size=10)

    result = await db_session.execute(select(OutboxMessage))
    outbox_msgs = result.scalars().all()
    assert len(outbox_msgs) >= 1
    assert "OrderCancelledEvent" in outbox_msgs[0].event_type


@pytest.mark.asyncio
async def test_sweep_batching(db_session):
    """Sweeper should process all stale orders across multiple batches."""
    old_time = datetime.now(UTC) - timedelta(minutes=30)

    for _ in range(5):
        order = _make_order(status=OrderStatus.PENDING.value, created_at=old_time)
        db_session.add(order)
    await db_session.commit()

    # Batch size of 2 should still process all 5 across multiple iterations
    timed_out = await sweep_stale_sagas(cutoff_minutes=15, batch_size=2)

    assert timed_out == 5
