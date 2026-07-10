import pytest
from app.models import User
from app.repository import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_user_repository_crud(db_session: AsyncSession):
    repo = UserRepository(db_session)

    # 1. Add user
    new_user = User(
        email="test@cloudscale.com",
        password_hash="hashed_pwd",
        first_name="Jane",
        last_name="Doe",
        role="shopper"
    )
    await repo.add(new_user)
    await db_session.flush()

    # 2. Query user by id
    retrieved = await repo.get_by_id(new_user.id)
    assert retrieved is not None
    assert retrieved.email == "test@cloudscale.com"
    assert retrieved.first_name == "Jane"

    # 3. Query user by email
    retrieved_by_email = await repo.get_by_email("test@cloudscale.com")
    assert retrieved_by_email is not None
    assert retrieved_by_email.id == new_user.id

    # 4. Check existence
    assert await repo.exists_by_email("test@cloudscale.com") is True
    assert await repo.exists_by_email("unknown@cloudscale.com") is False

    # 5. Remove user
    await repo.remove(new_user)
    await db_session.flush()
    assert await repo.get_by_id(new_user.id) is None
