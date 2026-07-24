"""Catalog Service - Business Service Layer.

Implements catalog management operations with a multi-layer Cache-Aside pattern (L1/L2)
and Circuit Breakers to handle database degradation gracefully.
"""

import uuid
from typing import Any, cast

import structlog
from app.config import settings
from app.models import Product
from app.repository import ProductRepository
from app.schemas import ProductCreate, ProductResponse
from cloudscale_shared import (
    CircuitBreaker,
    ConflictException,
    NotFoundException,
    ValidationException,
    cache_aside,
    circuit_breaker,
    get_current_tenant,
    retry_with_backoff,
)
from cloudscale_shared.query import Page, PageParams
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

# Circuit Breaker for protecting Database operations
db_breaker = CircuitBreaker(
    name="catalog_db_breaker",
    failure_threshold=5,
    recovery_timeout_seconds=15.0,
)


class CatalogService:
    """Service layer handling product catalog logic, resiliency, and caching."""

    def __init__(self, session: AsyncSession, redis: Redis | None = None):
        self.repo = ProductRepository(session)
        self.session = session
        self.redis = redis

    async def create_product(self, payload: ProductCreate) -> Product:
        """Creates a new catalog product with quota checks, then invalidates paginated caches."""
        tenant_id = get_current_tenant()

        plan_tier = "free"
        if self.redis:
            # Resolve active subscription limits from Redis plan context
            plan_raw = await self.redis.get(f"tenant:plan:{tenant_id}")
            plan_tier = plan_raw.decode() if isinstance(plan_raw, bytes) else (plan_raw or "free")

        limits = {"free": 10, "growth": 100, "enterprise": 10000}
        max_limit = limits.get(plan_tier, 10)

        current_count = await self.repo.count_tenant_products()
        if current_count >= max_limit:
            logger.warn("Product registration failed - Quota limit exceeded", tenant_id=tenant_id, plan_tier=plan_tier)
            raise ValidationException(
                f"Catalog item quota limit of {max_limit} exceeded for plan '{plan_tier}'. Please upgrade."
            )

        if await self.repo.exists_by_sku(payload.sku):
            logger.warn("Product registration failed - SKU already exists", sku=payload.sku)
            raise ConflictException("SKU already exists")

        new_product = Product(
            sku=payload.sku,
            name=payload.name,
            description=payload.description,
            price=payload.price,
            is_active=True,
            tenant_id=tenant_id,
        )
        await self.repo.add(new_product)
        await self.session.flush()

        # Invalidate all paginated lists cache
        await self._invalidate_list_caches()

        logger.info("Product catalog item created", product_id=str(new_product.id), tenant_id=new_product.tenant_id)
        return new_product

    async def bulk_create_products(self, items: list[ProductCreate], batch_size: int = 500) -> list[ProductResponse]:
        """Creates products in batches with pre-validation and atomic batch rollback."""
        tenant_id = get_current_tenant()
        created_products: list[Product] = []

        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]

            # Pre-validate batch items
            for idx, item in enumerate(batch):
                if not item.name or not item.sku or item.price < 0:
                    raise ValidationException(f"Invalid product payload at batch index {i + idx}")

            try:
                async with self.session.begin_nested():
                    for item in batch:
                        if await self.repo.exists_by_sku(item.sku):
                            raise ConflictException(f"SKU '{item.sku}' already exists")

                        product = Product(
                            sku=item.sku,
                            name=item.name,
                            description=item.description,
                            price=item.price,
                            is_active=True,
                            tenant_id=tenant_id,
                        )
                        await self.repo.add(product)
                        created_products.append(product)
                    await self.session.flush()
            except Exception:
                await self.session.rollback()
                raise

        await self._invalidate_list_caches()
        return [ProductResponse.model_validate(p) for p in created_products]

    async def get_product_by_id(self, product_id: uuid.UUID) -> ProductResponse:
        """Retrieves a product by ID, checking L1/L2 cache and circuit breaking database."""
        # Wrap database fetch with cache_aside using our shared wrapper
        # We define a helper that operates inside the cache scope

        @cache_aside(key_prefix="catalog_product", ttl_seconds=settings.PRODUCT_CACHE_TTL_SECONDS)
        async def _get_cached_product(pid_str: str) -> dict[str, Any]:
            product = await self._fetch_product_from_db(uuid.UUID(pid_str))
            return cast(dict[str, Any], ProductResponse.model_validate(product).model_dump())

        res_dict = await _get_cached_product(str(product_id))
        return ProductResponse.model_validate(res_dict)

    async def list_products(self, params: PageParams) -> Page[ProductResponse]:
        """Lists active products with pagination, checking cache and database."""

        @cache_aside(key_prefix="catalog_list", ttl_seconds=60)
        async def _get_cached_list(tenant_id: str, page: int, size: int) -> dict[str, Any]:
            items, total = await self._fetch_list_from_db(PageParams(page=page, size=size))
            product_responses = [ProductResponse.model_validate(p) for p in items]
            page_result = Page.create(product_responses, total, PageParams(page=page, size=size))
            return cast(dict[str, Any], page_result.model_dump())

        res_dict = await _get_cached_list(get_current_tenant(), params.page, params.size)
        return Page[ProductResponse].model_validate(res_dict)

    # ──────────────────────────────────────────────────────────────────────────────
    # Walled-off Resilient Database Fetch Methods
    # ──────────────────────────────────────────────────────────────────────────────

    @circuit_breaker(db_breaker)
    @retry_with_backoff("catalog_db_get", max_attempts=3)
    async def _fetch_product_from_db(self, product_id: uuid.UUID) -> Product:
        """Fetch product detail with retry and circuit breaker logic."""
        product = await self.repo.get_by_id(product_id)
        if not product or not product.is_active:
            raise NotFoundException("Product not found")
        return product

    @circuit_breaker(db_breaker)
    @retry_with_backoff("catalog_db_list", max_attempts=3)
    async def _fetch_list_from_db(self, params: PageParams) -> tuple[list[Product], int]:
        """Fetch paginated products with retry and circuit breaker logic."""
        items, total = await self.repo.list_active_paginated(params)
        return list(items), total

    # ──────────────────────────────────────────────────────────────────────────────
    # Cache Eviction Helpers
    # ──────────────────────────────────────────────────────────────────────────────

    async def _invalidate_list_caches(self) -> None:
        """Evicts list pages from Redis cache using O(1) version bumping."""
        try:
            from cloudscale_shared.cache import l1_cache

            l1_cache.clear()

            # Evict L2 entries
            redis = self.redis
            if redis is None:
                return
            keys = await redis.keys("v1:catalog_list:*")
            if keys:
                await redis.delete(*keys)
                logger.info("Evicted catalog list caches", count=len(keys))
        except Exception as e:
            logger.error("Failed to invalidate list caches", error=str(e))
