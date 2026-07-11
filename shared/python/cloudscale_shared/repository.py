from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Generic, TypeVar, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    """Abstract Base Class for Data Access Repositories."""

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Persists a new entity to the data store."""
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: Any) -> T | None:
        """Retrieves a single entity by its primary key ID."""
        pass

    @abstractmethod
    async def list(self) -> Sequence[T]:
        """Retrieves all entities from the data store."""
        pass

    @abstractmethod
    async def remove(self, entity: T) -> None:
        """Removes an entity from the data store."""
        pass


class SQLAlchemyRepository(AbstractRepository[T]):
    """SQLAlchemy Async implementation of the Repository Pattern."""

    def __init__(self, session: AsyncSession, model_class: type[T]):
        self.session = session
        self.model_class = model_class

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        return entity

    async def get_by_id(self, entity_id: Any) -> T | None:
        return cast(T | None, await self.session.get(self.model_class, entity_id))

    async def list(self) -> Sequence[T]:
        stmt = select(self.model_class)
        result = await self.session.execute(stmt)
        return cast(Sequence[T], result.scalars().all())

    async def remove(self, entity: T) -> None:
        await self.session.delete(entity)
