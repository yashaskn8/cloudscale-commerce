"""Chaos Engineering Simulator.

Simulates network dropouts, database degradation, and Redis caching outages
to verify that the platform degrades gracefully instead of crashing.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from cloudscale_shared import (
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitState,
    circuit_breaker,
)


@pytest.mark.asyncio
async def test_chaos_circuit_breaker_db_failure():
    """Verify that after repeated database failures, circuit breaker trips and blocks calls."""
    breaker = CircuitBreaker("chaos_db", failure_threshold=3, recovery_timeout_seconds=2.0)

    call_count = 0

    @circuit_breaker(breaker)
    async def flaky_db_call():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Database connection lost (Chaos Simulation)")

    # 1. Trigger failures up to threshold
    for i in range(3):
        with pytest.raises(ConnectionError):
            await flaky_db_call()

    # Breaker should now be OPEN
    assert breaker.state == CircuitState.OPEN

    # 2. Subsequent call should fail immediately with CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        await flaky_db_call()

    # The actual function should NOT have been entered on the 4th call
    assert call_count == 3

    # 3. Wait for recovery timeout to pass
    await asyncio.sleep(2.1)

    # Breaker should transition to HALF-OPEN on check
    breaker.check_state()
    assert breaker.state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_chaos_cache_aside_redis_outage():
    """Verify that Catalog service degrades gracefully to database reads when Redis is offline."""
    from app.service import CatalogService

    mock_session = AsyncMock()
    mock_redis = AsyncMock()

    # Mock Redis to raise connection error (simulating Redis down)
    mock_redis.get.side_effect = ConnectionError("Redis is unreachable")

    service = CatalogService(session=mock_session, redis=mock_redis)

    # Mock the database repository response
    mock_product = AsyncMock()
    mock_product.id = uuid_val = __import__("uuid").uuid4()
    mock_product.sku = "SKU-CHAOS-001"
    mock_product.name = "Chaos Widget"
    mock_product.description = "Flaky Redis Product"
    mock_product.price = __import__("decimal").Decimal("99.99")
    mock_product.is_active = True

    with patch.object(service.repo, "get_by_id", return_value=mock_product):
        # Call should succeed by falling back to DB, logging the Redis error
        res = await service.get_product_by_id(uuid_val)
        assert res is not None
        assert res.id == uuid_val
