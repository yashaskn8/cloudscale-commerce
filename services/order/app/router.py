"""Order Service — API Router.

Exposes endpoints to trigger order checkouts and query order state.
Uses transactional outbox — no direct Kafka dependency in the HTTP path.
"""

import uuid

import structlog
from app.schemas import OrderCreate, OrderResponse
from app.service import OrderService
from cloudscale_shared import ValidationException, get_db_session, get_redis_client
from fastapi import APIRouter, Depends, Header, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])

DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


def get_order_service(
    db: AsyncSession = Depends(get_db_session), redis: Redis = Depends(get_redis_client)
) -> OrderService:
    """FastAPI Dependency Injection for OrderService."""
    return OrderService(db, redis)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_order(
    payload: OrderCreate,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Initiates a checkout Saga by creating an order and writing to the outbox."""
    user_id_str = x_user_id or DEFAULT_USER_ID
    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise ValidationException("Invalid X-User-Id header format")

    logger.info(
        "Order checkout requested",
        user_id=user_id_str,
        idempotency_key=payload.idempotency_key,
    )
    order = await service.create_order(user_uuid, payload)
    return OrderResponse.model_validate(order)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Retrieve details for a specific order ID."""
    order = await service.get_order(order_id)
    return OrderResponse.model_validate(order)
