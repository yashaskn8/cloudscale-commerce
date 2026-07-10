import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Product
from app.repository import ProductRepository
from cloudscale_shared.query import PageParams


@pytest.mark.asyncio
async def test_product_repository_crud(db_session: AsyncSession):
    repo = ProductRepository(db_session)

    # 1. Add product
    product = Product(
        sku="SKU-TEST-001",
        name="Test Widget",
        description="A test widget for unit testing",
        price=Decimal("29.99"),
        is_active=True
    )
    await repo.add(product)
    await db_session.flush()

    # 2. Query by ID
    retrieved = await repo.get_by_id(product.id)
    assert retrieved is not None
    assert retrieved.sku == "SKU-TEST-001"
    assert retrieved.price == Decimal("29.99")

    # 3. Query by SKU
    retrieved_by_sku = await repo.get_by_sku("SKU-TEST-001")
    assert retrieved_by_sku is not None
    assert retrieved_by_sku.id == product.id

    # 4. Existence check
    assert await repo.exists_by_sku("SKU-TEST-001") is True
    assert await repo.exists_by_sku("SKU-NONEXISTENT") is False

    # 5. Paginated listing (active only)
    items, total = await repo.list_active_paginated(PageParams(page=1, size=10))
    assert total == 1
    assert len(items) == 1
    assert items[0].sku == "SKU-TEST-001"

    # 6. Deactivated product excluded from active listing
    product.is_active = False
    await db_session.flush()
    items_after, total_after = await repo.list_active_paginated(PageParams(page=1, size=10))
    assert total_after == 0
    assert len(items_after) == 0

    # 7. Remove product
    await repo.remove(product)
    await db_session.flush()
    assert await repo.get_by_id(product.id) is None
