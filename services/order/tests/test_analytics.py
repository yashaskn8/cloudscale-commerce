"""Unit tests for Order Service analytics endpoint."""

import uuid
from decimal import Decimal

import pytest
from app.schemas import OrderCreate, OrderItemCreate
from app.service import OrderService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_order_analytics_empty(db_session: AsyncSession):
    service = OrderService(db_session)
    res = await service.get_analytics()
    assert res.total_orders == 0
    assert res.total_revenue == Decimal("0.0")
    assert res.average_order_value == Decimal("0.0")
    assert res.top_selling_items == []


@pytest.mark.asyncio
async def test_order_analytics_populated(db_session: AsyncSession):
    service = OrderService(db_session)
    user_id = uuid.uuid4()
    p1, p2 = uuid.uuid4(), uuid.uuid4()

    # Create order 1
    o1 = OrderCreate(
        items=[
            OrderItemCreate(product_id=p1, quantity=2, unit_price=Decimal("50.00")),
            OrderItemCreate(product_id=p2, quantity=1, unit_price=Decimal("100.00")),
        ],
        idempotency_key="test-key-analytics-1",
    )
    await service.create_order(user_id, o1)

    # Create order 2
    o2 = OrderCreate(
        items=[
            OrderItemCreate(product_id=p1, quantity=3, unit_price=Decimal("50.00")),
        ],
        idempotency_key="test-key-analytics-2",
    )
    await service.create_order(user_id, o2)
    await db_session.commit()

    analytics = await service.get_analytics(top_n=5)
    assert analytics.total_orders == 2
    assert analytics.total_revenue == Decimal("350.00")
    assert analytics.average_order_value == Decimal("175.00")
    assert len(analytics.top_selling_items) == 2
    # p1 total qty = 2 + 3 = 5
    assert analytics.top_selling_items[0].product_id == p1
    assert analytics.top_selling_items[0].total_quantity_sold == 5
