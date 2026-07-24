"""Inventory Service - Business Service Layer.

Coordinates stock queries and updates.
Uses distributed locking (Redis Redlock-like) to protect critical restock blocks.
"""

import uuid

import structlog
from app.locking import acquire_lock
from app.models import Inventory
from app.repository import InventoryRepository
from app.schemas import RestockRequest
from cloudscale_shared import NotFoundException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()
LOCK_KEY_PREFIX = "inventory:lock:"


class InventoryService:
    """Service layer handling inventory updates and queries."""

    def __init__(self, session: AsyncSession, redis: Redis):
        self.repo = InventoryRepository(session)
        self.session = session
        self.redis = redis

    async def get_inventory(self, product_id: uuid.UUID) -> Inventory:
        """Query inventory level for a single product ID."""
        inventory = await self.repo.get_by_product_id(product_id)
        if not inventory:
            raise NotFoundException("Inventory record not found for this product")
        return inventory

    async def restock(self, product_id: uuid.UUID, payload: RestockRequest) -> Inventory:
        """Restocks a product, acquiring a distributed lock on Redis first."""
        lock_key = f"{LOCK_KEY_PREFIX}{product_id}"

        async with acquire_lock(self.redis, lock_key):
            inventory = await self.repo.get_by_product_id(product_id)
            if not inventory:
                logger.info("No prior inventory entry. Creating new restock entry.", product_id=str(product_id))
                inventory = Inventory(product_id=product_id, available_stock=payload.quantity, reserved_stock=0)
                await self.repo.add(inventory)
            else:
                inventory.available_stock += payload.quantity
                inventory.version += 1

            await self.session.flush()
            logger.info("Restock successful", product_id=str(product_id), new_stock=inventory.available_stock)
            return inventory
