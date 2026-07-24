from collections.abc import Generator

import pytest
from app.main import app
from app.router import get_auth_service
from app.service import AuthService
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def test_app(db_session: AsyncSession) -> Generator[FastAPI, None, None]:
    """Fixture that overrides database injection to use the test session."""

    def get_test_auth_service():
        return AuthService(db_session)

    app.dependency_overrides[get_auth_service] = get_test_auth_service
    yield app
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_router_endpoints(test_app: FastAPI):
    # Use ASGITransport for testing FastAPI app directly
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register User via REST API with policy-compliant password
        register_payload = {
            "email": "router_test@cloudscale.com",
            "password": "SecurePass123!",
            "first_name": "Bob",
            "last_name": "Builder",
        }
        res = await client.post("/api/v1/auth/register", json=register_payload)
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == "router_test@cloudscale.com"
        assert "id" in data

        # Check security headers (OWASP)
        assert res.headers.get("X-Frame-Options") == "DENY"
        assert res.headers.get("X-Content-Type-Options") == "nosniff"

        # 2. Login via REST API
        login_payload = {"email": "router_test@cloudscale.com", "password": "SecurePass123!"}
        res = await client.post("/api/v1/auth/login", json=login_payload)
        assert res.status_code == 200
        tokens = res.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # 3. Test Refresh Token Rotation
        refresh_payload = {"refresh_token": refresh_token}
        res_refresh = await client.post("/api/v1/auth/refresh", json=refresh_payload)
        assert res_refresh.status_code == 200
        new_tokens = res_refresh.json()
        assert "access_token" in new_tokens
        assert new_tokens["access_token"] != access_token

        # 4. Test RBAC: List users endpoint requires 'admin' role header
        # Request without role header -> 403 Forbidden
        headers = {"Authorization": f"Bearer {access_token}"}
        res_users = await client.get("/api/v1/auth/users", headers=headers)
        assert res_users.status_code == 403

        # Request with correct role header -> 200 OK
        admin_headers = {"Authorization": f"Bearer {access_token}", "X-User-Roles": "admin"}
        res_users_admin = await client.get("/api/v1/auth/users", headers=admin_headers)
        assert res_users_admin.status_code == 200
        users_data = res_users_admin.json()
        assert "items" in users_data
        assert len(users_data["items"]) >= 1

        # 5. Test Logout (Token revocation check)
        res_logout = await client.post("/api/v1/auth/logout", headers=headers)
        assert res_logout.status_code == 204
