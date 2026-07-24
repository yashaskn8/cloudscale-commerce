# ADR-001: Dual Payment Processing Model

**Status:** Accepted  
**Date:** 2026-07-11  
**Authors:** CloudScale Commerce Team

## Context

The Payment Service needs to support two operational modes:

1. **Simulated mode** — for development, staging, and demo environments where real Stripe charges should not occur.
2. **Real mode** — for production, using the Stripe PaymentIntent API with webhook verification.

Without a clear boundary, simulated payment logic could silently execute in production, creating a false sense of successful order completion while no real charges are being made.

## Decision

We introduce a `SIMULATE_PAYMENTS` boolean flag (default: `True`) in the Payment Service configuration (`services/payment/app/config.py`).

### Behavior

| `SIMULATE_PAYMENTS` | Environment | Behavior |
|---|---|---|
| `True` (default) | Dev, Staging | Simulated charge with `sim_txn_*` IDs, deterministic failure on `quantity=99` |
| `False` | Production | Raises `NotImplementedError` until real Stripe integration is wired |

### Key Design Choices

- **Fail-closed in production:** Setting `SIMULATE_PAYMENTS=False` without wiring Stripe will raise a clear error rather than silently succeeding.
- **Explicit transaction ID prefix:** Simulated transactions use `sim_txn_` prefix, making them trivially distinguishable from real charges in logs and database records.
- **No conditional import:** Both paths live in `consumers.py` to avoid module-level branching that complicates testing.

## Consequences

### Positive
- Impossible to accidentally run simulated payments in production (the `NotImplementedError` will surface immediately in logs and monitoring).
- Demo and staging environments work out of the box without Stripe credentials.
- Simulated transactions are visually distinct in all observability surfaces.

### Negative
- Requires a real Stripe integration to be wired before `SIMULATE_PAYMENTS=False` can be used in production.
- The `NotImplementedError` approach means the service will crash on the first payment event if misconfigured — this is intentional (fail-fast).

## Related Files
- `services/payment/app/config.py` — `SIMULATE_PAYMENTS` setting
- `services/payment/app/consumers.py` — Payment processing logic with dual paths
- `services/payment/app/router.py` — Stripe webhook endpoint
