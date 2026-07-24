import uuid
from decimal import Decimal

import pytest
from app.models import Order, OrderItem
from app.repository import OrderRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_order_repository_crud(db_session: AsyncSession):
    repo = OrderRepository(db_session)
    user_id = uuid.uuid4()

    # 1. Create order
    order = Order(user_id=user_id, status="PENDING", total_amount=Decimal("59.98"), idempotency_key="idem-key-test-001")
    await repo.add(order)
    await db_session.flush()

    # Save child item
    item = OrderItem(order_id=order.id, product_id=uuid.uuid4(), quantity=2, unit_price=Decimal("29.99"))
    db_session.add(item)
    await db_session.flush()

    # 2. Query by ID
    retrieved = await repo.get_by_id(order.id)
    assert retrieved is not None
    assert retrieved.status == "PENDING"
    assert retrieved.total_amount == Decimal("59.98")

    # 3. Query by idempotency key
    by_key = await repo.get_by_idempotency_key("idem-key-test-001")
    assert by_key is not None
    assert by_key.id == order.id

    # 4. Non-existent idempotency key returns None
    missing = await repo.get_by_idempotency_key("idem-key-nonexistent")
    assert missing is None

    # 5. Update order status
    order.status = "CONFIRMED"
    await db_session.flush()
    updated = await repo.get_by_id(order.id)
    assert updated is not None
    assert updated.status == "CONFIRMED"
