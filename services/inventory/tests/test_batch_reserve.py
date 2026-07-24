"""Unit tests for Inventory atomic batch reservation and OCC retries."""

import uuid
from unittest.mock import AsyncMock

import pytest
from app.schemas import BatchReserveItem, RestockRequest
from app.service import InventoryService
from cloudscale_shared.exceptions import ValidationException
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_reserve_batch_success(db_session: AsyncSession):
    mock_redis = AsyncMock()
    service = InventoryService(db_session, mock_redis)

    pid1, pid2 = uuid.uuid4(), uuid.uuid4()
    await service.restock(pid1, RestockRequest(quantity=50))
    await service.restock(pid2, RestockRequest(quantity=30))
    await db_session.commit()

    items = [
        BatchReserveItem(product_id=pid1, quantity=10),
        BatchReserveItem(product_id=pid2, quantity=5),
    ]

    reserved = await service.reserve_batch(items)
    assert len(reserved) == 2
    assert reserved[0].available_stock == 40
    assert reserved[1].available_stock == 25


@pytest.mark.asyncio
async def test_reserve_batch_insufficient_stock_rollback(db_session: AsyncSession):
    mock_redis = AsyncMock()
    service = InventoryService(db_session, mock_redis)

    pid1, pid2 = uuid.uuid4(), uuid.uuid4()
    await service.restock(pid1, RestockRequest(quantity=50))
    await service.restock(pid2, RestockRequest(quantity=5))
    await db_session.commit()

    items = [
        BatchReserveItem(product_id=pid1, quantity=10),
        BatchReserveItem(product_id=pid2, quantity=100),  # Insufficient
    ]

    with pytest.raises(ValidationException):
        await service.reserve_batch(items)

    # Verify pid1 stock was NOT decremented due to atomic rollback
    inv1 = await service.get_inventory(pid1)
    assert inv1.available_stock == 50
