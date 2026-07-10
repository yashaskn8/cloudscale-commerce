"""Catalog Service - Product Repository.

Handles database querying and state changes for Product aggregates.
"""
from collections.abc import Sequence

from app.models import Product
from cloudscale_shared import get_current_tenant
from cloudscale_shared.query import PageParams
from cloudscale_shared.repository import SQLAlchemyRepository
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class ProductRepository(SQLAlchemyRepository[Product]):
    """Repository for Product entity data access."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Product)

    async def get_by_sku(self, sku: str) -> Product | None:
        """Retrieves a product by its unique SKU within current tenant context."""
        stmt = (
            select(Product)
            .where(Product.sku == sku)
            .where(Product.tenant_id == get_current_tenant())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active_paginated(self, params: PageParams) -> tuple[Sequence[Product], int]:
        """Retrieves a paginated list of active products and total count under current tenant."""
        tenant = get_current_tenant()

        # Count active products in tenant
        count_stmt = (
            select(func.count())
            .select_from(Product)
            .where(Product.is_active == True)
            .where(Product.tenant_id == tenant)
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Paginated data in tenant
        data_stmt = (
            select(Product)
            .where(Product.is_active == True)
            .where(Product.tenant_id == tenant)
            .order_by(Product.name.asc())
            .offset(params.offset)
            .limit(params.size)
        )
        result = await self.session.execute(data_stmt)
        items = result.scalars().all()
        return items, total

    async def exists_by_sku(self, sku: str) -> bool:
        """Checks if a product with the given SKU exists in current tenant."""
        stmt = (
            select(func.count())
            .select_from(Product)
            .where(Product.sku == sku)
            .where(Product.tenant_id == get_current_tenant())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def count_tenant_products(self) -> int:
        """Counts all active products belonging to the current tenant."""
        stmt = (
            select(func.count())
            .select_from(Product)
            .where(Product.is_active == True)
            .where(Product.tenant_id == get_current_tenant())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
