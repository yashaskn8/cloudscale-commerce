"""Auth Service - User Repository.

Encapsulates all database access operations for the User aggregate root.
Extends the shared SQLAlchemyRepository with domain-specific query methods.
"""
from collections.abc import Sequence

from app.models import User
from cloudscale_shared.query import PageParams
from cloudscale_shared.repository import SQLAlchemyRepository
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository(SQLAlchemyRepository[User]):
    """Repository for User entity data access."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        """Retrieves a user by their email address."""
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_paginated(self, params: PageParams) -> tuple[Sequence[User], int]:
        """Returns a paginated list of users and the total count."""
        # Count query
        count_stmt = select(func.count()).select_from(User)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Data query
        data_stmt = (
            select(User)
            .order_by(User.created_at.desc())
            .offset(params.offset)
            .limit(params.size)
        )
        result = await self.session.execute(data_stmt)
        items = result.scalars().all()
        return items, total

    async def exists_by_email(self, email: str) -> bool:
        """Checks if a user with the given email already exists."""
        stmt = select(func.count()).select_from(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0
