"""Production-Grade Multi-Layer Distributed Caching (L1 Local + L2 Redis).

Provides:
- Two-tier caching with L1 in-memory TTL cache and L2 Redis cluster cache
- Cache-Aside decorator pattern
- Cache Stampede (Thundering Herd) prevention via Single-Flight locks
- Cache key versioning
- Dynamic cache warming
- Invalidation helper hooks
- Prometheus metrics monitoring for hit/miss ratios
"""
import asyncio
import json
import time
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, TypeVar

import structlog
from prometheus_client import Counter

logger = structlog.get_logger()

# ──────────────────────────────────────────────────────────────────────────────
# Prometheus Caching Metrics
# ──────────────────────────────────────────────────────────────────────────────

CACHE_REQUESTS = Counter(
    "caching_requests_total",
    "Total requests sent to the caching layer",
    ["tier", "operation", "status"]  # tier: L1/L2, status: hit/miss
)

# Cache Key Versioning
CACHE_VERSION = "v1"

T = TypeVar("T")


class L1LocalCache:
    """Fast in-memory cache to prevent Redis network call congestion."""

    def __init__(self, default_ttl_seconds: float = 5.0):
        self._store: dict[str, tuple[Any, float]] = {}
        self.default_ttl = default_ttl_seconds

    def get(self, key: str) -> Any | None:
        """Retrieves item if present and not expired."""
        if key not in self._store:
            return None
        value, expiry = self._store[key]
        if time.time() > expiry:
            del self._store[key]  # Clean up expired entry
            return None
        return value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Stores item with explicit expiration timestamp."""
        duration = ttl if ttl is not None else self.default_ttl
        self._store[key] = (value, time.time() + duration)

    def delete(self, key: str) -> None:
        """Evicts key from local memory cache."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Flushes L1 store completely."""
        self._store.clear()


# Instantiate L1 singleton
l1_cache = L1LocalCache()

# Single-flight locks dictionary to prevent Cache Stampedes
_single_flight_locks: dict[str, asyncio.Lock] = {}


def _get_single_flight_lock(key: str) -> asyncio.Lock:
    """Returns lock bound to a cache key to coordinate concurrent database fetches."""
    if key not in _single_flight_locks:
        _single_flight_locks[key] = asyncio.Lock()
    return _single_flight_locks[key]


def serialize_args(*args: Any, **kwargs: Any) -> str:
    """Helper creating a deterministic string from arguments for key construction."""
    arg_str = ":".join(str(arg) for arg in args)
    kwarg_str = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return f"{arg_str}:{kwarg_str}"


def cache_aside(
    key_prefix: str,
    ttl_seconds: int = 300,
    l1_ttl_seconds: int = 5,
) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
    """Decorator applying multi-layer cache-aside lookup with stampede lock protection."""
    def decorator(
        func: Callable[..., Coroutine[Any, Any, Any]]
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Construct versioned cache key
            args_identity = serialize_args(*args, **kwargs)
            cache_key = f"{CACHE_VERSION}:{key_prefix}:{func.__name__}:{args_identity}"

            # ── 1. Check L1 Memory Cache ──────────────────────────────────────
            l1_val = l1_cache.get(cache_key)
            if l1_val is not None:
                CACHE_REQUESTS.labels(tier="L1", operation=key_prefix, status="hit").inc()
                return l1_val
            CACHE_REQUESTS.labels(tier="L1", operation=key_prefix, status="miss").inc()

            # ── 2. Check L2 Redis Cache ────────────────────────────────────────
            from cloudscale_shared.database import redis_manager

            redis_client = None
            if redis_manager is not None:
                try:
                    redis_client = redis_manager.get_client()
                    redis_val = await redis_client.get(cache_key)
                    if redis_val:
                        val = json.loads(redis_val)
                        # Warm L1 cache
                        l1_cache.set(cache_key, val, ttl=l1_ttl_seconds)
                        CACHE_REQUESTS.labels(tier="L2", operation=key_prefix, status="hit").inc()
                        return val
                except Exception as exc:
                    logger.warn("Redis L2 read failure", error=str(exc))

            CACHE_REQUESTS.labels(tier="L2", operation=key_prefix, status="miss").inc()

            # ── 3. Cache Miss (With Cache Stampede Single-Flight Lock) ─────────
            sf_lock = _get_single_flight_lock(cache_key)
            async with sf_lock:
                # Double-check inside lock to see if another concurrent thread warmed the cache
                l1_val = l1_cache.get(cache_key)
                if l1_val is not None:
                    return l1_val

                if redis_client:
                    try:
                        redis_val = await redis_client.get(cache_key)
                        if redis_val:
                            val = json.loads(redis_val)
                            l1_cache.set(cache_key, val, ttl=l1_ttl_seconds)
                            return val
                    except Exception:
                        pass

                # Fetch from primary database
                logger.info(
                    "Cache miss. Fetching payload from primary database.",
                    key=cache_key,
                )
                db_result = await func(*args, **kwargs)

                # Warm L1 and L2 caches with fetched result
                l1_cache.set(cache_key, db_result, ttl=l1_ttl_seconds)
                if redis_client:
                    try:
                        await redis_client.setex(
                            cache_key, ttl_seconds, json.dumps(db_result)
                        )
                    except Exception as exc:
                        logger.error("Failed to write to L2 Redis cache", error=str(exc))

                return db_result
        return wrapper
    return decorator


# ──────────────────────────────────────────────────────────────────────────────
# Invalidation Helpers
# ──────────────────────────────────────────────────────────────────────────────

async def invalidate_cache_key(key_prefix: str, func_name: str, args_identity: str) -> None:
    """Evicts a specific cache key from both local and distributed cache levels."""
    cache_key = f"{CACHE_VERSION}:{key_prefix}:{func_name}:{args_identity}"
    l1_cache.delete(cache_key)

    from cloudscale_shared.database import redis_manager
    if redis_manager:
        try:
            redis_client = redis_manager.get_client()
            await redis_client.delete(cache_key)
            logger.info("Evicted cache key successfully", key=cache_key)
        except Exception as exc:
            logger.error("Failed to invalidate Redis key", key=cache_key, error=str(exc))
