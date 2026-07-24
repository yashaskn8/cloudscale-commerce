from collections.abc import AsyncGenerator

import app.consumers
import cloudscale_shared.database
import pytest
from app.models import Base
from cloudscale_shared.database import DatabaseSessionManager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


@pytest.fixture(autouse=True)
async def configure_global_db_manager(test_session_manager):
    """Overrides the global db_manager and the local consumers db_manager reference."""
    original_shared_manager = cloudscale_shared.database.db_manager
    original_consumers_manager = app.consumers.db_manager

    cloudscale_shared.database.db_manager = test_session_manager
    app.consumers.db_manager = test_session_manager

    yield

    cloudscale_shared.database.db_manager = original_shared_manager
    app.consumers.db_manager = original_consumers_manager


import os


@pytest.fixture
async def test_engine():
    """Create engine for testing. Fallback to SQLite in-memory if no DATABASE_URL is set."""
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        engine = create_async_engine(db_url, echo=False)
    else:
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False}, echo=False
        )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine

    # Drop tables for clean state in subsequent runs on persistent DBs
    if engine.url.drivername.startswith("postgresql"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_session_manager(test_engine) -> DatabaseSessionManager:
    """Fixture that overrides database manager to use the configured test engine."""
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    manager = DatabaseSessionManager(db_url)
    manager._write_engine = test_engine
    manager._read_engine = test_engine
    manager._write_sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    manager._read_sessionmaker = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    return manager


@pytest.fixture
async def db_session(test_session_manager) -> AsyncGenerator[AsyncSession, None]:
    """Generates an AsyncSession linked to the in-memory test database."""
    async with test_session_manager.session() as session:
        yield session
        await session.rollback()
