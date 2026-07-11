from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import Any, Self

from sqlalchemy.ext.asyncio import AsyncSession

from cloudscale_shared.database import DatabaseSessionManager


class AbstractUnitOfWork(ABC):
    """Abstract Context Manager for transaction tracking (Unit of Work)."""

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    @abstractmethod
    async def commit(self) -> None:
        """Commits the active transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rolls back the active transaction."""
        pass


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """SQLAlchemy implementation of the Unit of Work Pattern."""

    def __init__(self, session_manager: DatabaseSessionManager):
        self.session_manager = session_manager
        self.session: AsyncSession | None = None
        self._session_ctx: AbstractAsyncContextManager[AsyncSession] | None = None

    async def __aenter__(self) -> Self:
        # Start session context
        self._session_ctx = self.session_manager.session()
        self.session = await self._session_ctx.__aenter__()
        return await super().__aenter__()

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> None:
        try:
            await super().__aexit__(exc_type, exc_val, exc_tb)
        finally:
            if self._session_ctx:
                await self._session_ctx.__aexit__(exc_type, exc_val, exc_tb)
            self.session = None
            self._session_ctx = None

    async def commit(self) -> None:
        if self.session:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session:
            await self.session.rollback()
