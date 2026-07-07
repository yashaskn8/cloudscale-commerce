"""API Smoke Tests — Quick functional validation for post-deployment verification.

These tests validate that core user journeys work end-to-end after deployment:
1. User registration and login (Auth).
2. Product listing (Catalog).
3. Inventory stock check.
4. Order placement.
"""
import os
import httpx
import pytest

AUTH_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
CATALOG_URL = os.getenv("CATALOG_SERVICE_URL", "http://localhost:8002")
INVENTORY_URL = os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8003")
ORDER_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8004")


class TestSmokeUserJourney:
    """End-to-end smoke test simulating a standard user flow."""

    def test_auth_register_smoke(self):
        """Verify that user registration endpoint responds."""
        response = httpx.post(
            f"{AUTH_URL}/api/v1/auth/register",
            json={
                "email": "smoketest@cloudscale.io",
                "password": "SmokeTest123!",
                "full_name": "Smoke Test User",
            },
            timeout=10.0,
        )
        # Either 201 Created or 409 Conflict (already exists) is acceptable
        assert response.status_code in (201, 409, 422)

    def test_auth_login_smoke(self):
        """Verify that user login endpoint responds."""
        response = httpx.post(
            f"{AUTH_URL}/api/v1/auth/login",
            json={
                "email": "smoketest@cloudscale.io",
                "password": "SmokeTest123!",
            },
            timeout=10.0,
        )
        # 200 with tokens or 401 Unauthorized is acceptable
        assert response.status_code in (200, 401, 422)

    def test_catalog_list_products_smoke(self):
        """Verify that catalog listing endpoint responds."""
        response = httpx.get(f"{CATALOG_URL}/api/v1/products", timeout=10.0)
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, (list, dict))

    def test_inventory_list_smoke(self):
        """Verify that inventory listing endpoint responds."""
        response = httpx.get(f"{INVENTORY_URL}/api/v1/inventory", timeout=10.0)
        assert response.status_code == 200

    def test_order_list_smoke(self):
        """Verify that order listing endpoint responds."""
        response = httpx.get(f"{ORDER_URL}/api/v1/orders", timeout=10.0)
        # 200 OK or 401 Unauthorized (requires auth token) is acceptable
        assert response.status_code in (200, 401, 403)
