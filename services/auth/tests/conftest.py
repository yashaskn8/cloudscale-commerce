import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models import Base
from cloudscale_shared.database import DatabaseSessionManager


@pytest.fixture
async def test_engine():
    """Create in-memory SQLite engine for fast testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session_manager(test_engine) -> DatabaseSessionManager:
    """Fixture that overrides database manager to use the in-memory SQLite engine."""
    manager = DatabaseSessionManager("sqlite+aiosqlite:///:memory:")
    manager._write_engine = test_engine
    manager._read_engine = test_engine
    manager._write_sessionmaker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    manager._read_sessionmaker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    return manager


@pytest.fixture
async def db_session(test_session_manager) -> AsyncGenerator[AsyncSession, None]:
    """Generates an AsyncSession linked to the in-memory test database."""
    async with test_session_manager.session() as session:
        yield session
        await session.rollback()
