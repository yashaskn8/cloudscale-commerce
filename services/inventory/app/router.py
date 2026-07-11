"""Inventory Service - API Router.

Exposes endpoints to query stock and restock products.
Integrates dependency-injected InventoryService.
"""

import uuid

import structlog
from app.schemas import InventoryResponse, RestockRequest
from app.service import InventoryService
from cloudscale_shared import get_db_session, get_redis_client
from cloudscale_shared.security import RoleChecker
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/inventory", tags=["Inventory"])


def get_inventory_service(
    db: AsyncSession = Depends(get_db_session), redis: Redis = Depends(get_redis_client)
) -> InventoryService:
    """FastAPI Dependency Injection for InventoryService."""
    return InventoryService(db, redis)


@router.get("/{product_id}", response_model=InventoryResponse)
async def get_inventory(
    product_id: uuid.UUID, service: InventoryService = Depends(get_inventory_service)
) -> InventoryResponse:
    """Retrieve current stock levels for a product."""
    inventory = await service.get_inventory(product_id)
    return InventoryResponse.model_validate(inventory)


@router.post(
    "/{product_id}/restock",
    response_model=InventoryResponse,
    dependencies=[Depends(RoleChecker(["merchant", "admin"]))],
)
async def restock(
    product_id: uuid.UUID, payload: RestockRequest, service: InventoryService = Depends(get_inventory_service)
) -> InventoryResponse:
    """Restocks inventory levels for a product (Requires merchant or admin role)."""
    inventory = await service.restock(product_id, payload)
    return InventoryResponse.model_validate(inventory)
