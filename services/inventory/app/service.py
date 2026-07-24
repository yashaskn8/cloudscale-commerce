"""Inventory Service - Business Service Layer.

Coordinates stock queries and updates.
Uses distributed locking (Redis Redlock-like) to protect critical restock blocks.
"""

import uuid

import structlog
from app.locking import acquire_lock
from app.models import Inventory
from app.repository import InventoryRepository
from app.schemas import BatchReserveItem, RestockRequest
from cloudscale_shared import NotFoundException
from prometheus_client import Counter
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()
LOCK_KEY_PREFIX = "inventory:lock:"
INVENTORY_LOW_STOCK_TOTAL = Counter("inventory_low_stock_total", "Total low stock alert events")


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

    async def reserve_batch(self, items: list[BatchReserveItem], max_retries: int = 3) -> list[Inventory]:
        """Atomically reserves stock for a batch of items with OCC retries and low-stock alerts."""
        from cloudscale_shared.exceptions import ConflictException, ValidationException
        from sqlalchemy.orm.exc import StaleDataError

        for attempt in range(max_retries):
            try:
                async with self.session.begin_nested():
                    reserved_records: list[Inventory] = []

                    for item in items:
                        inventory = await self.repo.get_by_product_id(item.product_id)
                        if not inventory or inventory.available_stock < item.quantity:
                            avail = inventory.available_stock if inventory else 0
                            raise ValidationException(
                                f"Insufficient stock for product {item.product_id}. "
                                f"Requested: {item.quantity}, Available: {avail}"
                            )

                        inventory.available_stock -= item.quantity
                        inventory.reserved_stock += item.quantity
                        inventory.version += 1
                        reserved_records.append(inventory)

                        if inventory.available_stock < 10:
                            INVENTORY_LOW_STOCK_TOTAL.inc()
                            logger.warn(
                                "Low stock threshold reached",
                                product_id=str(item.product_id),
                                remaining_stock=inventory.available_stock,
                            )

                    await self.session.flush()
                    logger.info("Batch stock reservation successful", item_count=len(items))
                    return reserved_records
            except StaleDataError:
                await self.session.rollback()
                if attempt == max_retries - 1:
                    logger.error("OCC conflict: Max retries exceeded during batch reservation")
                    raise ConflictException("Concurrent inventory update conflict. Please retry.")
                logger.warn("OCC conflict detected, retrying batch reservation", attempt=attempt + 1)
            except Exception:
                await self.session.rollback()
                raise

        raise ConflictException("Concurrent inventory update conflict. Please retry.")
