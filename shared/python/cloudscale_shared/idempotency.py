"""CloudScale Commerce — Core Idempotency Primitives.

Provides deterministic request fingerprinting, Redis-backed key locking, and
cached response retrieval for idempotent API operations.
"""

import hashlib
import json
from typing import Any, cast

import structlog

from cloudscale_shared.exceptions import CloudScaleException

logger = structlog.get_logger()

DEFAULT_IDEMPOTENCY_TTL_SECONDS = 86400  # 24 hours


def compute_request_fingerprint(
    method: str, path: str, tenant_id: str | None, payload: dict[str, Any] | bytes | str | None
) -> str:
    """Computes a deterministic SHA-256 digest of an HTTP request context."""
    hasher = hashlib.sha256()
    hasher.update(method.upper().encode("utf-8"))
    hasher.update(path.encode("utf-8"))
    hasher.update((tenant_id or "global").encode("utf-8"))

    if payload is not None:
        if isinstance(payload, dict):
            canonical_json = json.dumps(payload, sort_keys=True)
            hasher.update(canonical_json.encode("utf-8"))
        elif isinstance(payload, bytes):
            hasher.update(payload)
        elif isinstance(payload, str):
            hasher.update(payload.encode("utf-8"))

    return hasher.hexdigest()


class IdempotencyManager:
    """Redis-backed idempotency record manager enforcing payload consistency and preventing duplicate processing."""

    def __init__(self, redis_client: Any, ttl_seconds: int = DEFAULT_IDEMPOTENCY_TTL_SECONDS):
        self.redis = redis_client
        self.ttl = ttl_seconds

    def _format_key(self, tenant_id: str | None, key: str) -> str:
        tenant = tenant_id or "global"
        return f"idempotency:{tenant}:{key}"

    async def start_processing(
        self, tenant_id: str | None, idempotency_key: str, fingerprint: str
    ) -> dict[str, Any] | None:
        """Attempts to register or lock an idempotency key.

        Returns cached response dict if already COMPLETED.
        Raises 409 Conflict if payload mismatch or request IN_PROGRESS.
        """
        redis_key = self._format_key(tenant_id, idempotency_key)
        existing_data = await self.redis.get(redis_key)

        if existing_data:
            record = cast(dict[str, Any], json.loads(existing_data))
            if record.get("fingerprint") != fingerprint:
                logger.warn(
                    "Idempotency key payload mismatch",
                    idempotency_key=idempotency_key,
                    tenant_id=tenant_id,
                )
                raise CloudScaleException(
                    message="Idempotency key reused with different request payload",
                    code="IDEMPOTENCY_KEY_MISMATCH",
                    status_code=409,
                )

            if record.get("status") == "IN_PROGRESS":
                logger.warn(
                    "Concurrent idempotent request in progress",
                    idempotency_key=idempotency_key,
                    tenant_id=tenant_id,
                )
                raise CloudScaleException(
                    message="Concurrent request in progress with this idempotency key",
                    code="IDEMPOTENCY_CONCURRENT_REQUEST",
                    status_code=409,
                )

            if record.get("status") == "COMPLETED":
                logger.info(
                    "Returning cached idempotent response",
                    idempotency_key=idempotency_key,
                    tenant_id=tenant_id,
                )
                return record

        # Register in-progress request atomically
        in_progress_record = {
            "fingerprint": fingerprint,
            "status": "IN_PROGRESS",
            "status_code": None,
            "body": None,
        }
        await self.redis.set(redis_key, json.dumps(in_progress_record), ex=self.ttl)
        return None

    async def save_response(
        self, tenant_id: str | None, idempotency_key: str, fingerprint: str, status_code: int, body: dict[str, Any]
    ) -> None:
        """Saves the completed response into Redis under the idempotency key."""
        redis_key = self._format_key(tenant_id, idempotency_key)
        completed_record = {
            "fingerprint": fingerprint,
            "status": "COMPLETED",
            "status_code": status_code,
            "body": body,
        }
        await self.redis.set(redis_key, json.dumps(completed_record), ex=self.ttl)

    async def clear_key(self, tenant_id: str | None, idempotency_key: str) -> None:
        """Removes the idempotency key (used on processing failure to allow retry)."""
        redis_key = self._format_key(tenant_id, idempotency_key)
        await self.redis.delete(redis_key)
