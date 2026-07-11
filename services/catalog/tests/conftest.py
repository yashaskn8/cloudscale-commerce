import os
from collections.abc import AsyncGenerator

import pytest
from app.models import Base
from cloudscale_shared.database import DatabaseSessionManager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
async def test_engine():
    """Create engine for testing. Fallback to SQLite in-memory if no DATABASE_URL is set."""
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(db_url, echo=False)
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
