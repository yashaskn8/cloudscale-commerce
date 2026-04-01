"""Inventory Service - Inventory Repository.

Handles database operations on the Inventory aggregate.
"""
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cloudscale_shared.repository import SQLAlchemyRepository
from app.models import Inventory


class InventoryRepository(SQLAlchemyRepository[Inventory]):
    """Repository for Inventory entity data access."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Inventory)

    async def get_by_product_id(self, product_id: uuid.UUID) -> Inventory | None:
        """Retrieves inventory details for a specific product ID."""
        stmt = select(Inventory).where(Inventory.product_id == product_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
