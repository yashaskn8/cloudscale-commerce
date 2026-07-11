"""
Billing & Subscription Router — Payment Service.

Provides subscription management, invoice history, entitlement checking,
and a production-grade Stripe webhook receiver with HMAC-SHA256 signature
verification and replay attack protection.
"""

import hashlib
import hmac
import json
import time
from decimal import Decimal

import structlog
from app.models import Invoice, Subscription
from cloudscale_shared import get_current_tenant, get_db_session
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])

# Stripe webhook signing secret — loaded from settings
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET

PLAN_LIMITS = {
    "free": {"max_products": 10, "max_orders": 15},
    "growth": {"max_products": 100, "max_orders": 200},
    "enterprise": {"max_products": 10000, "max_orders": 20000},
}

# Maps Stripe price IDs to internal plan tiers
STRIPE_PRICE_TO_TIER = {
    "price_free_monthly": "free",
    "price_growth_monthly": "growth",
    "price_enterprise_monthly": "enterprise",
}


# ── Stripe Signature Verification ───────────────────────────────────────────────


def verify_stripe_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """
    Verify Stripe webhook signature using HMAC-SHA256.

    Stripe sends a `Stripe-Signature` header containing:
      t=<timestamp>,v1=<signature>

    We reconstruct the signed payload as `<timestamp>.<payload>` and compare
    the HMAC-SHA256 digest against the provided signature.

    Timing tolerance: rejects events older than 5 minutes to prevent replay attacks.
    """
    if not signature_header:
        return False

    try:
        parts = {}
        for item in signature_header.split(","):
            key, value = item.strip().split("=", 1)
            parts[key] = value

        timestamp = parts.get("t")
        expected_sig = parts.get("v1")

        if not timestamp or not expected_sig:
            return False

        # Replay attack protection: reject events older than 300 seconds
        event_age = int(time.time()) - int(timestamp)
        if event_age > 300:
            logger.warn("Stripe webhook replay detected", age_seconds=event_age)
            return False

        # Reconstruct signed payload and compute HMAC
        signed_payload = f"{timestamp}.".encode() + payload
        computed_sig = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()

        return hmac.compare_digest(computed_sig, expected_sig)

    except (ValueError, KeyError) as e:
        logger.error("Stripe signature parsing failed", error=str(e))
        return False


# ── Subscription Endpoints ──────────────────────────────────────────────────────


@router.get("/subscriptions/active")
async def get_active_subscription(db: AsyncSession = Depends(get_db_session)):
    """Retrieve the active subscription for the current tenant context."""
    tenant = get_current_tenant()
    res = await db.execute(select(Subscription).where(Subscription.tenant_id == tenant))
    sub = res.scalar_one_or_none()

    if not sub:
        sub = Subscription(tenant_id=tenant, plan_tier="free", status="active")
        db.add(sub)
        await db.commit()

    return {
        "tenant_id": sub.tenant_id,
        "plan_tier": sub.plan_tier,
        "status": sub.status,
        "limits": PLAN_LIMITS.get(sub.plan_tier, PLAN_LIMITS["free"]),
    }


@router.post("/subscriptions")
async def update_subscription(plan_tier: str, db: AsyncSession = Depends(get_db_session)):
    """Subscribe or transition the active tenant to a new pricing plan tier."""
    if plan_tier not in ["free", "growth", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid plan tier specified")

    tenant = get_current_tenant()
    res = await db.execute(select(Subscription).where(Subscription.tenant_id == tenant))
    sub = res.scalar_one_or_none()

    if not sub:
        sub = Subscription(tenant_id=tenant, plan_tier=plan_tier, status="active")
        db.add(sub)
    else:
        sub.plan_tier = plan_tier
        sub.status = "active"

    invoice_amounts = {"free": 0.00, "growth": 49.00, "enterprise": 299.00}
    invoice = Invoice(tenant_id=tenant, amount=Decimal(invoice_amounts[plan_tier]), currency="USD", status="paid")
    db.add(invoice)
    await db.commit()

    return {"status": "success", "plan_tier": sub.plan_tier, "invoice_id": str(invoice.id)}


@router.get("/invoices")
async def get_invoices(db: AsyncSession = Depends(get_db_session)):
    """Retrieve billing invoices history for the current tenant."""
    tenant = get_current_tenant()
    res = await db.execute(select(Invoice).where(Invoice.tenant_id == tenant))
    invoices = res.scalars().all()
    return invoices


@router.get("/entitlements")
async def get_entitlements(db: AsyncSession = Depends(get_db_session)):
    """Check active entitlement metrics against subscription quota limits."""
    tenant = get_current_tenant()
    res = await db.execute(select(Subscription).where(Subscription.tenant_id == tenant))
    sub = res.scalar_one_or_none()
    tier = sub.plan_tier if sub else "free"

    return {"tenant_id": tenant, "plan_tier": tier, "limits": PLAN_LIMITS.get(tier, PLAN_LIMITS["free"])}


# ── Stripe Webhook Receiver ────────────────────────────────────────────────────


@router.post("/webhooks/stripe", status_code=status.HTTP_200_OK)
async def handle_stripe_webhook(request: Request, db: AsyncSession = Depends(get_db_session)):
    """
    Process incoming Stripe webhook events with cryptographic signature verification.

    Supported event types:
      - customer.subscription.created: Provision new subscription
      - customer.subscription.updated: Handle plan changes, cancellations
      - invoice.payment_succeeded: Record successful payment
      - invoice.payment_failed: Mark subscription as past_due

    Security:
      - HMAC-SHA256 signature verification against webhook signing secret
      - Replay attack protection (5-minute timestamp tolerance)
      - Idempotent processing (upsert on tenant_id)
    """
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    if not verify_stripe_signature(payload, signature, STRIPE_WEBHOOK_SECRET):
        logger.warn("Stripe webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event.get("type", "")
    event_data = event.get("data", {}).get("object", {})
    tenant_id = event_data.get("metadata", {}).get("tenant_id", "unknown")

    logger.info("Stripe webhook received", event_type=event_type, tenant_id=tenant_id)

    # ── Event Routing ────────────────────────────────────────────────────────

    if event_type == "customer.subscription.created":
        price_id = event_data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id", "")
        tier = STRIPE_PRICE_TO_TIER.get(price_id, "free")

        res = await db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        sub = res.scalar_one_or_none()

        if not sub:
            sub = Subscription(tenant_id=tenant_id, plan_tier=tier, status="active")
            db.add(sub)
        else:
            sub.plan_tier = tier
            sub.status = "active"

        await db.commit()
        logger.info("Subscription provisioned via webhook", tenant_id=tenant_id, tier=tier)

    elif event_type == "customer.subscription.updated":
        cancel_at_period_end = event_data.get("cancel_at_period_end", False)
        price_id = event_data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id", "")
        tier = STRIPE_PRICE_TO_TIER.get(price_id, "free")

        res = await db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        sub = res.scalar_one_or_none()

        if sub:
            sub.plan_tier = tier
            sub.status = "cancelled" if cancel_at_period_end else "active"
            await db.commit()

    elif event_type == "invoice.payment_succeeded":
        amount = Decimal(str(event_data.get("amount_paid", 0))) / 100  # Stripe sends cents
        invoice = Invoice(
            tenant_id=tenant_id, amount=amount, currency=event_data.get("currency", "usd").upper(), status="paid"
        )
        db.add(invoice)
        await db.commit()

    elif event_type == "invoice.payment_failed":
        res = await db.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        sub = res.scalar_one_or_none()
        if sub:
            sub.status = "past_due"
            await db.commit()
            logger.warn("Payment failed, subscription marked past_due", tenant_id=tenant_id)

    else:
        logger.info("Unhandled Stripe event type", event_type=event_type)

    return {"status": "received", "event_type": event_type}
