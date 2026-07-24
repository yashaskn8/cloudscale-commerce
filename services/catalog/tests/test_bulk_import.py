"""Unit tests for Catalog bulk import and cache invalidation."""

import pytest
from app.schemas import ProductCreate
from app.service import CatalogService
from cloudscale_shared.exceptions import ConflictException
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_bulk_create_products_success(db_session: AsyncSession):
    service = CatalogService(db_session)
    items = [
        ProductCreate(sku=f"BULK-SKU-{i}", name=f"Bulk Product {i}", description="Desc", price=19.99) for i in range(5)
    ]

    results = await service.bulk_create_products(items, batch_size=2)
    assert len(results) == 5
    assert results[0].sku == "BULK-SKU-0"
    assert results[4].sku == "BULK-SKU-4"


@pytest.mark.asyncio
async def test_bulk_create_products_duplicate_sku_rollback(db_session: AsyncSession):
    service = CatalogService(db_session)
    # Create initial product
    await service.create_product(ProductCreate(sku="EXISTING-SKU", name="Prod 1", description="D", price=10.0))

    items = [
        ProductCreate(sku="NEW-SKU-1", name="New Product", description="Desc", price=10.0),
        ProductCreate(sku="EXISTING-SKU", name="Duplicate Product", description="Desc", price=15.0),
    ]

    with pytest.raises(ConflictException):
        await service.bulk_create_products(items)
