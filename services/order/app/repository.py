"""Order Service - Order Repository.

Handles database querying and state persistence for Order aggregates.
"""
import uuid

from app.models import Order
from cloudscale_shared import get_current_tenant
from cloudscale_shared.repository import SQLAlchemyRepository
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class OrderRepository(SQLAlchemyRepository[Order]):
    """Repository for Order entity data access."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Order)

    async def get_by_idempotency_key(self, key: str) -> Order | None:
        """Retrieves an order by its unique idempotency key within tenant context."""
        stmt = (
            select(Order)
            .where(Order.idempotency_key == key)
            .where(Order.tenant_id == get_current_tenant())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tenant_orders(self) -> list[Order]:
        """Retrieves all orders associated with the active tenant context."""
        stmt = select(Order).where(Order.tenant_id == get_current_tenant()).order_by(Order.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_orders(self, user_id: uuid.UUID) -> list[Order]:
        """Retrieves all orders matching the user ID and tenant context."""
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .where(Order.tenant_id == get_current_tenant())
            .order_by(Order.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_tenant_orders(self) -> int:
        """Counts all orders belonging to the current tenant."""
        stmt = (
            select(func.count())
            .select_from(Order)
            .where(Order.tenant_id == get_current_tenant())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
