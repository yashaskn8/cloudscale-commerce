import pytest
from app.main import app
from app.models import Subscription
from cloudscale_shared.middleware import tenant_id_context
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


@pytest.mark.asyncio
async def test_billing_subscription_flow(db_session):
    # Set active tenant context
    token = tenant_id_context.set("tenant-test-123")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Get active subscription (should default to free and insert it)
            response = await ac.get("/api/v1/billing/subscriptions/active", headers={"X-Tenant-ID": "tenant-test-123"})
            assert response.status_code == 200
            data = response.json()
            assert data["plan_tier"] == "free"
            assert data["status"] == "active"
            assert data["limits"]["max_products"] == 10

            # Verify in db
            res = await db_session.execute(select(Subscription).where(Subscription.tenant_id == "tenant-test-123"))
            sub = res.scalar_one_or_none()
            assert sub is not None
            assert sub.plan_tier == "free"

            # 2. Update subscription to growth
            response = await ac.post(
                "/api/v1/billing/subscriptions?plan_tier=growth", headers={"X-Tenant-ID": "tenant-test-123"}
            )
            assert response.status_code == 200
            res_data = response.json()
            assert res_data["status"] == "success"
            assert res_data["plan_tier"] == "growth"

            # 3. Check active subscription has updated limits
            response = await ac.get("/api/v1/billing/subscriptions/active", headers={"X-Tenant-ID": "tenant-test-123"})
            assert response.status_code == 200
            data = response.json()
            assert data["plan_tier"] == "growth"
            assert data["limits"]["max_products"] == 100

            # 4. Check invoices history
            response = await ac.get("/api/v1/billing/invoices", headers={"X-Tenant-ID": "tenant-test-123"})
            assert response.status_code == 200
            invoices = response.json()
            assert len(invoices["items"]) == 1
            assert float(invoices["items"][0]["amount"]) == 49.00

    finally:
        tenant_id_context.reset(token)
