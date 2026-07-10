import uuid

import pytest
from app.models import Inventory
from app.repository import InventoryRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_inventory_repository_crud(db_session: AsyncSession):
    repo = InventoryRepository(db_session)
    product_id = uuid.uuid4()

    # 1. Add inventory record
    inventory = Inventory(
        product_id=product_id,
        available_stock=100,
        reserved_stock=0,
        version=1
    )
    await repo.add(inventory)
    await db_session.flush()

    # 2. Query by product_id
    retrieved = await repo.get_by_product_id(product_id)
    assert retrieved is not None
    assert retrieved.available_stock == 100
    assert retrieved.reserved_stock == 0

    # 3. Update stock
    retrieved.available_stock += 50
    retrieved.version += 1
    await db_session.flush()

    updated = await repo.get_by_product_id(product_id)
    assert updated is not None
    assert updated.available_stock == 150
    assert updated.version == 2

    # 4. Non-existent product returns None
    missing = await repo.get_by_product_id(uuid.uuid4())
    assert missing is None
