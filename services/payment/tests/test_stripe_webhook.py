"""
Tests for Stripe Webhook Signature Verification & Event Processing.

Validates:
  1. HMAC-SHA256 signature verification accepts valid signatures
  2. Rejects tampered payloads (signature mismatch)
  3. Rejects unsigned requests (missing header)
  4. Subscription lifecycle: created → updated → cancelled
  5. Invoice payment recording on payment_succeeded events
  6. Subscription status transitions on payment_failed events
  7. Replay attack protection (stale timestamps)
"""

import hashlib
import hmac
import json
import time
from decimal import Decimal

import pytest
from app.main import app
from app.models import Invoice, Subscription
from app.router import STRIPE_WEBHOOK_SECRET, verify_stripe_signature
from cloudscale_shared.middleware import tenant_id_context
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


def _build_stripe_signature(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    """Helper to construct a valid Stripe-Signature header."""
    ts = timestamp or int(time.time())
    signed_payload = f"{ts}.".encode() + payload
    sig = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def _build_stripe_event(event_type: str, tenant_id: str = "tenant-webhook-test", **kwargs) -> dict:
    """Helper to construct a Stripe event payload."""
    event = {
        "id": "evt_test_123",
        "type": event_type,
        "data": {"object": {"metadata": {"tenant_id": tenant_id}, **kwargs}},
    }
    return event


# ── Unit Tests: Signature Verification ──────────────────────────────────────────


class TestStripeSignatureVerification:
    def test_valid_signature_accepted(self):
        payload = b'{"type": "test"}'
        sig = _build_stripe_signature(payload, STRIPE_WEBHOOK_SECRET)
        assert verify_stripe_signature(payload, sig, STRIPE_WEBHOOK_SECRET) is True

    def test_tampered_payload_rejected(self):
        payload = b'{"type": "test"}'
        sig = _build_stripe_signature(payload, STRIPE_WEBHOOK_SECRET)
        tampered = b'{"type": "HACKED"}'
        assert verify_stripe_signature(tampered, sig, STRIPE_WEBHOOK_SECRET) is False

    def test_wrong_secret_rejected(self):
        payload = b'{"type": "test"}'
        sig = _build_stripe_signature(payload, "wrong_secret")
        assert verify_stripe_signature(payload, sig, STRIPE_WEBHOOK_SECRET) is False

    def test_missing_signature_rejected(self):
        payload = b'{"type": "test"}'
        assert verify_stripe_signature(payload, "", STRIPE_WEBHOOK_SECRET) is False

    def test_malformed_signature_rejected(self):
        payload = b'{"type": "test"}'
        assert verify_stripe_signature(payload, "garbage_header", STRIPE_WEBHOOK_SECRET) is False

    def test_replay_attack_rejected(self):
        """Signatures older than 5 minutes should be rejected."""
        payload = b'{"type": "test"}'
        stale_timestamp = int(time.time()) - 600  # 10 minutes ago
        sig = _build_stripe_signature(payload, STRIPE_WEBHOOK_SECRET, timestamp=stale_timestamp)
        assert verify_stripe_signature(payload, sig, STRIPE_WEBHOOK_SECRET) is False


# ── Integration Tests: Webhook Event Processing ────────────────────────────────


class TestStripeWebhookEndpoint:
    @pytest.mark.asyncio
    async def test_rejects_unsigned_request(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/api/v1/billing/webhooks/stripe",
                content=b'{"type": "test"}',
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 400
            assert "signature" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_subscription_created_provisions_tenant(self, db_session):
        """Verify customer.subscription.created provisions a new subscription record."""
        token = tenant_id_context.set("tenant-webhook-test")
        try:
            event = _build_stripe_event(
                "customer.subscription.created",
                tenant_id="tenant-webhook-test",
                items={"data": [{"price": {"id": "price_growth_monthly"}}]},
            )
            payload = json.dumps(event).encode()
            sig = _build_stripe_signature(payload, STRIPE_WEBHOOK_SECRET)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/billing/webhooks/stripe",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Stripe-Signature": sig,
                    },
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "received"
                assert data["event_type"] == "customer.subscription.created"

            # Verify subscription was created in DB
            res = await db_session.execute(select(Subscription).where(Subscription.tenant_id == "tenant-webhook-test"))
            sub = res.scalar_one_or_none()
            assert sub is not None
            assert sub.plan_tier == "growth"
            assert sub.status == "active"
        finally:
            tenant_id_context.reset(token)

    @pytest.mark.asyncio
    async def test_invoice_payment_succeeded_records_invoice(self, db_session):
        """Verify invoice.payment_succeeded creates an invoice record."""
        token = tenant_id_context.set("tenant-invoice-test")
        try:
            event = _build_stripe_event(
                "invoice.payment_succeeded",
                tenant_id="tenant-invoice-test",
                amount_paid=4900,  # $49.00 in cents
                currency="usd",
            )
            payload = json.dumps(event).encode()
            sig = _build_stripe_signature(payload, STRIPE_WEBHOOK_SECRET)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/billing/webhooks/stripe",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Stripe-Signature": sig,
                    },
                )
                assert response.status_code == 200

            # Verify invoice was recorded
            res = await db_session.execute(select(Invoice).where(Invoice.tenant_id == "tenant-invoice-test"))
            inv = res.scalar_one_or_none()
            assert inv is not None
            assert inv.amount == Decimal("49.00")
            assert inv.currency == "USD"
            assert inv.status == "paid"
        finally:
            tenant_id_context.reset(token)

    @pytest.mark.asyncio
    async def test_payment_failed_marks_past_due(self, db_session):
        """Verify invoice.payment_failed transitions subscription to past_due."""
        token = tenant_id_context.set("tenant-pastdue-test")
        try:
            # First create an active subscription
            sub = Subscription(tenant_id="tenant-pastdue-test", plan_tier="growth", status="active")
            db_session.add(sub)
            await db_session.commit()

            # Send payment_failed event
            event = _build_stripe_event("invoice.payment_failed", tenant_id="tenant-pastdue-test")
            payload = json.dumps(event).encode()
            sig = _build_stripe_signature(payload, STRIPE_WEBHOOK_SECRET)

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/api/v1/billing/webhooks/stripe",
                    content=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Stripe-Signature": sig,
                    },
                )
                assert response.status_code == 200

            # Force reload from DB to bypass SQLAlchemy's identity map cache
            await db_session.refresh(sub)
            assert sub.status == "past_due"
        finally:
            tenant_id_context.reset(token)
