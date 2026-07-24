"""Catalog Service - API Router.

Exposes endpoints for querying catalog items, adding new ones, and performing AI recommendations.
"""

import uuid
from typing import cast

import structlog
from app.ai import ProductSearchService
from app.schemas import ProductCreate, ProductResponse
from app.service import CatalogService
from cloudscale_shared import get_db_session, get_redis_client
from cloudscale_shared.query import Page, PageParams
from cloudscale_shared.security import RoleChecker
from fastapi import APIRouter, Depends, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/products", tags=["Catalog"])


def get_catalog_service(
    db: AsyncSession = Depends(get_db_session), redis: Redis = Depends(get_redis_client)
) -> CatalogService:
    """FastAPI Dependency Injection for CatalogService."""
    return CatalogService(db, redis)


def get_ai_service(
    db: AsyncSession = Depends(get_db_session), redis: Redis = Depends(get_redis_client)
) -> ProductSearchService:
    """FastAPI Dependency Injection for ProductSearchService."""
    return ProductSearchService(db, redis)


@router.get("", response_model=Page[ProductResponse])
async def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    service: CatalogService = Depends(get_catalog_service),
) -> Page[ProductResponse]:
    """Retrieve all active catalog products with pagination."""
    params = PageParams(page=page, size=size)
    return await service.list_products(params)


@router.get("/recommendations", response_model=list[ProductResponse])
async def get_recommendations(
    product_id: uuid.UUID,
    limit: int = Query(3, ge=1, le=10),
    ai_service: ProductSearchService = Depends(get_ai_service),
) -> list[ProductResponse]:
    """Retrieve AI-powered recommendations matching the target product ID."""
    return cast(list[ProductResponse], await ai_service.get_recommendations(product_id, limit))


@router.get("/search/semantic", response_model=list[ProductResponse])
async def semantic_search(
    query: str, limit: int = Query(5, ge=1, le=20), ai_service: ProductSearchService = Depends(get_ai_service)
) -> list[ProductResponse]:
    """Perform a fuzzy semantic embedding search simulator."""
    return cast(list[ProductResponse], await ai_service.semantic_search(query, limit))


@router.get("/search/suggestions", response_model=list[str])
async def get_suggestions(prefix: str, ai_service: ProductSearchService = Depends(get_ai_service)) -> list[str]:
    """Retrieve autocomplete product suggestions matching a name query prefix."""
    return cast(list[str], await ai_service.get_suggestions(prefix))


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: uuid.UUID, service: CatalogService = Depends(get_catalog_service)) -> ProductResponse:
    """Retrieve product details by product ID."""
    return await service.get_product_by_id(product_id)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["merchant", "admin"]))],
)
async def create_product(
    payload: ProductCreate, service: CatalogService = Depends(get_catalog_service)
) -> ProductResponse:
    """Create a new product in the catalog (Requires merchant or admin role)."""
    product = await service.create_product(payload)
    return ProductResponse.model_validate(product)


@router.post(
    "/bulk",
    response_model=list[ProductResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["merchant", "admin"]))],
)
async def bulk_create_products(
    payload: list[ProductCreate], service: CatalogService = Depends(get_catalog_service)
) -> list[ProductResponse]:
    """Bulk create catalog products in 500-item batch transactions (Requires merchant or admin role)."""
    return cast(list[ProductResponse], await service.bulk_create_products(payload))
