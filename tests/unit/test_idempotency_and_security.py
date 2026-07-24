"""Unit tests for Phase 1 shared library additions (IdempotencyManager & Token Revocation)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from cloudscale_shared.exceptions import CloudScaleException, UnauthorizedException
from cloudscale_shared.idempotency import IdempotencyManager, compute_request_fingerprint
from cloudscale_shared.security import create_token_pair, decode_and_verify_token, revoke_token


@pytest.mark.asyncio
async def test_compute_request_fingerprint_deterministic():
    fp1 = compute_request_fingerprint("POST", "/api/v1/orders", "tenant-1", {"item": "A", "qty": 1})
    fp2 = compute_request_fingerprint("POST", "/api/v1/orders", "tenant-1", {"qty": 1, "item": "A"})
    assert fp1 == fp2  # Canonical JSON sorting ensures match

    fp_diff = compute_request_fingerprint("POST", "/api/v1/orders", "tenant-1", {"item": "B", "qty": 1})
    assert fp1 != fp_diff


@pytest.mark.asyncio
async def test_idempotency_manager_flow():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # First call: no key exists

    mgr = IdempotencyManager(mock_redis, ttl_seconds=60)
    fp = compute_request_fingerprint("POST", "/api/v1/orders", "tenant-1", {"total": 100})

    # Start processing
    result = await mgr.start_processing("tenant-1", "key-123", fp)
    assert result is None
    mock_redis.set.assert_called_once()

    # Save completed response
    await mgr.save_response("tenant-1", "key-123", fp, 201, {"order_id": "ord-1"})
    assert mock_redis.set.call_count == 2


@pytest.mark.asyncio
async def test_idempotency_manager_payload_mismatch():
    mock_redis = AsyncMock()
    # Simulate existing record with different fingerprint
    mock_redis.get.return_value = '{"fingerprint": "fp-old", "status": "COMPLETED", "status_code": 200, "body": {}}'

    mgr = IdempotencyManager(mock_redis)

    with pytest.raises(CloudScaleException) as exc_info:
        await mgr.start_processing("tenant-1", "key-123", "fp-new")
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "IDEMPOTENCY_KEY_MISMATCH"


@pytest.mark.asyncio
async def test_decode_and_verify_token_revocation():
    secret = "super-secret-key-min-32-chars-long"
    access_token, _ = create_token_pair("user-1", "customer", secret)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Token not revoked

    payload = await decode_and_verify_token(access_token, secret, redis_client=mock_redis)
    assert payload["sub"] == "user-1"

    # Simulate token revoked
    mock_redis.get.return_value = b"1"
    with pytest.raises(UnauthorizedException):
        await decode_and_verify_token(access_token, secret, redis_client=mock_redis)
