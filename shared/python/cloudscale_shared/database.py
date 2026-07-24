import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from prometheus_client import Gauge
from redis.asyncio import ConnectionPool, Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = structlog.get_logger()

# Connection Pool Metrics
DB_CONNECTIONS_ACTIVE = Gauge(
    "db_active_sessions",
    "Current active database sessions created by the session manager",
    ["service", "type"],  # read/write session label
)


class DatabaseSessionManager:
    """Manages primary/replica database engines, session routing, and connection pool sizes."""

    def __init__(
        self,
        write_url: str,
        read_url: str | None = None,
        service_name: str = "unknown",
        engine_kwargs: dict[str, Any] | None = None,
    ):
        self.service_name = service_name
        engine_kwargs = engine_kwargs or {}

        # High-performance enterprise production engine parameters
        engine_kwargs.setdefault("pool_pre_ping", True)
        if "sqlite" not in write_url:
            engine_kwargs.setdefault("pool_size", 20)
            engine_kwargs.setdefault("max_overflow", 40)
            engine_kwargs.setdefault("pool_recycle", 1800)  # Recycle after 30 mins
            engine_kwargs.setdefault("pool_timeout", 30)

        # Initialize Primary Write Engine
        self._write_engine = create_async_engine(write_url, **engine_kwargs)
        self._write_sessionmaker = async_sessionmaker(
            bind=self._write_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
        )

        # Initialize Read Replica Engine (Fallback to Write if not provided)
        self._read_url = read_url or write_url
        self._read_engine = create_async_engine(self._read_url, **engine_kwargs)
        self._read_sessionmaker = async_sessionmaker(
            bind=self._read_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False
        )

        logger.info(
            "Database session manager initialized",
            service=service_name,
            has_replica=read_url is not None,
        )

    async def close(self) -> None:
        """Disposes write and read database pools."""
        if self._write_engine:
            await self._write_engine.dispose()
        if self._read_engine:
            await self._read_engine.dispose()
        logger.info("Database engines successfully disposed.")

    @asynccontextmanager
    async def write_session(self, tenant_id: str | None = None) -> AsyncIterator[AsyncSession]:
        """Provides transaction block on primary writable database instance.

        If tenant_id is provided and the engine is PostgreSQL, sets the session variable
        'app.current_tenant_id' via SET LOCAL so RLS policies filter by tenant.
        """
        DB_CONNECTIONS_ACTIVE.labels(service=self.service_name, type="write").inc()
        session = self._write_sessionmaker()
        try:
            if tenant_id and self._write_engine.dialect.name == "postgresql":
                await session.execute(
                    text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                    {"tid": tenant_id},
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            DB_CONNECTIONS_ACTIVE.labels(service=self.service_name, type="write").dec()

    @asynccontextmanager
    async def read_session(self, tenant_id: str | None = None) -> AsyncIterator[AsyncSession]:
        """Provides query-only block routing queries to the read replica.

        If tenant_id is provided and the engine is PostgreSQL, sets the session variable
        'app.current_tenant_id' via SET LOCAL so RLS policies filter by tenant.
        """
        DB_CONNECTIONS_ACTIVE.labels(service=self.service_name, type="read").inc()
        session = self._read_sessionmaker()
        try:
            if tenant_id and self._read_engine.dialect.name == "postgresql":
                await session.execute(
                    text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                    {"tid": tenant_id},
                )
            yield session
        finally:
            await session.close()
            DB_CONNECTIONS_ACTIVE.labels(service=self.service_name, type="read").dec()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Backward compatibility helper routing to primary write sessions."""
        async with self.write_session() as session:
            yield session


# Redis Manager
class RedisManager:
    """Manages asynchronous Redis connection pool lifecycle."""

    def __init__(self, url: str):
        self.pool = ConnectionPool.from_url(
            url, decode_responses=True, max_connections=50  # Increased for higher load profiles
        )

    async def close(self) -> None:
        """Closes the Redis connection pool."""
        await self.pool.disconnect()
        logger.info("Redis connection pool disconnected.")

    def get_client(self) -> Redis:
        """Returns an async Redis client."""
        return Redis(connection_pool=self.pool)


# Global instances to be initialized during service lifespan
db_manager: DatabaseSessionManager | None = None
redis_manager: RedisManager | None = None


def init_db(database_url: str) -> None:
    """Initializes primary write/read session engines."""
    global db_manager
    # Read replica URL can be passed via DB_READ_REPLICA_URL environment variable
    read_replica_url = os.environ.get("DB_READ_REPLICA_URL")
    service_name = os.environ.get("SERVICE_NAME", "unknown")
    db_manager = DatabaseSessionManager(
        write_url=database_url,
        read_url=read_replica_url,
        service_name=service_name,
    )


def init_redis(redis_url: str) -> None:
    global redis_manager
    redis_manager = RedisManager(redis_url)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Dependency helper providing primary database session with RLS tenant context."""
    if db_manager is None:
        raise RuntimeError("Database session manager is not initialized.")
    # Import here to avoid circular dependency at module level
    from cloudscale_shared.security import current_tenant_id

    tenant = current_tenant_id.get(None)
    async with db_manager.write_session(tenant_id=tenant) as session:
        yield session


async def get_read_db_session() -> AsyncIterator[AsyncSession]:
    """Dependency helper providing query-only replica session with RLS tenant context."""
    if db_manager is None:
        raise RuntimeError("Database session manager is not initialized.")
    from cloudscale_shared.security import current_tenant_id

    tenant = current_tenant_id.get(None)
    async with db_manager.read_session(tenant_id=tenant) as session:
        yield session


async def get_redis_client() -> AsyncIterator[Redis]:
    """Dependency helper to get an async Redis client."""
    if redis_manager is None:
        raise RuntimeError("Redis manager is not initialized.")
    client = redis_manager.get_client()
    try:
        yield client
    finally:
        await client.aclose()


# ──────────────────────────────────────────────────────────────────────────────
# Cursor Pagination Helper
# ──────────────────────────────────────────────────────────────────────────────


async def cursor_paginate(
    session: AsyncSession,
    query_base: Any,
    column: Any,
    cursor: Any | None = None,
    limit: int = 20,
    descending: bool = False,
) -> tuple[list[Any], Any | None]:
    """Performs high-performance database offset-free cursor pagination.

    Returns:
        tuple (items, next_cursor)
    """
    stmt = query_base
    if cursor is not None:
        if descending:
            stmt = stmt.where(column < cursor)
        else:
            stmt = stmt.where(column > cursor)

    # Order and limit (+1 to detect if next page exists)
    order_expr = column.desc() if descending else column.asc()
    stmt = stmt.order_by(order_expr).limit(limit + 1)

    res = await session.execute(stmt)
    items = list(res.scalars().all())

    next_cursor = None
    if len(items) > limit:
        next_cursor = getattr(items[limit - 1], column.name)
        items = items[:limit]

    return items, next_cursor
