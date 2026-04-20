import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from cloudscale_shared import ConflictException, UnauthorizedException, ValidationException
from cloudscale_shared.security import verify_password
from app.service import AuthService
from app.schemas import UserRegister, UserLogin


@pytest.mark.asyncio
async def test_auth_service_operations(db_session: AsyncSession):
    service = AuthService(db_session)

    # 1. Password policy violation check (fails uppercase/special characters check, but passes length)
    invalid_register = UserRegister(
        email="weak@cloudscale.com",
        password="password123",
        first_name="Weak",
        last_name="Password"
    )
    with pytest.raises(ValidationException):
        await service.register_user(invalid_register)

    # 2. Register User with compliant password
    register_payload = UserRegister(
        email="service_test@cloudscale.com",
        password="SecurePass123!",
        first_name="Alice",
        last_name="Wonderland"
    )
    user = await service.register_user(register_payload)
    assert user.id is not None
    assert user.email == "service_test@cloudscale.com"
    assert verify_password("SecurePass123!", user.password_hash) is True

    # 3. Prevent duplicate registration
    with pytest.raises(ConflictException):
        await service.register_user(register_payload)

    # 4. Authenticate User (Successful)
    login_payload = UserLogin(
        email="service_test@cloudscale.com",
        password="SecurePass123!"
    )
    tokens = await service.authenticate_user(login_payload)
    assert tokens.access_token is not None
    assert tokens.refresh_token is not None

    # 5. Authenticate User (Failed password)
    bad_login = UserLogin(
        email="service_test@cloudscale.com",
        password="wrong_password"
    )
    with pytest.raises(UnauthorizedException):
        await service.authenticate_user(bad_login)
