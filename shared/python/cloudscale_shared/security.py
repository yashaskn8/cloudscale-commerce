"""Production-Grade Security Module.

Provides:
- Argon2id password hashing (OWASP recommended)
- JWT token creation, decoding, rotation, and Redis-backed revocation
- RBAC FastAPI dependency (RoleChecker)
- Redis-based rate limiter dependency
- Security headers middleware (OWASP best practices)
- Account lockout tracking
- Audit logging helpers
"""
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import structlog
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Header, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from cloudscale_shared.exceptions import (
    CloudScaleException,
    ForbiddenException,
    UnauthorizedException,
)

logger = structlog.get_logger()

# ──────────────────────────────────────────────────────────────────────────────
# Password Hashing (Argon2id)
# ──────────────────────────────────────────────────────────────────────────────

_ph = PasswordHasher(
    time_cost=3,        # iterations
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hashes a password using Argon2id with OWASP-recommended parameters."""
    return _ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against its Argon2id hash.

    Returns True on match, False on mismatch. Handles legacy bcrypt hashes
    by detecting the $2b$ prefix and falling back to passlib for migration.
    """
    # Legacy bcrypt detection for graceful migration
    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        try:
            from passlib.context import CryptContext
            legacy_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return legacy_ctx.verify(plain_password, hashed_password)
        except Exception:
            return False

    try:
        return _ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def password_needs_rehash(hashed_password: str) -> bool:
    """Checks if a stored hash should be upgraded to current Argon2id parameters."""
    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        return True  # Legacy bcrypt should be rehashed
    return _ph.check_needs_rehash(hashed_password)


# ──────────────────────────────────────────────────────────────────────────────
# Password Policy Validation
# ──────────────────────────────────────────────────────────────────────────────

def validate_password_policy(password: str) -> list[str]:
    """Validates password against enterprise security policy.

    Returns a list of violation messages. Empty list means the password is valid.
    """
    violations: list[str] = []
    if len(password) < 8:
        violations.append("Password must be at least 8 characters long.")
    if len(password) > 128:
        violations.append("Password must not exceed 128 characters.")
    if not any(c.isupper() for c in password):
        violations.append("Password must contain at least one uppercase letter.")
    if not any(c.islower() for c in password):
        violations.append("Password must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in password):
        violations.append("Password must contain at least one digit.")
    if not any(c in "!@#$%^&*()-_=+[]{}|;:',.<>?/`~" for c in password):
        violations.append("Password must contain at least one special character.")
    return violations


# ──────────────────────────────────────────────────────────────────────────────
# JWT Token Management
# ──────────────────────────────────────────────────────────────────────────────

def create_token_pair(
    user_id: str,
    role: str,
    secret_key: str,
    algorithm: str = "HS256",
    access_expire_minutes: int = 15,
    refresh_expire_days: int = 7,
) -> tuple[str, str]:
    """Creates an access/refresh JWT token pair."""
    utc_now = datetime.now(UTC)
    jti_access = str(uuid.uuid4())
    jti_refresh = str(uuid.uuid4())

    access_payload = {
        "sub": user_id,
        "role": role,
        "exp": int((utc_now + timedelta(minutes=access_expire_minutes)).timestamp()),
        "iat": int(utc_now.timestamp()),
        "jti": jti_access,
        "type": "access",
    }
    access_token = jwt.encode(access_payload, secret_key, algorithm=algorithm)

    refresh_payload = {
        "sub": user_id,
        "role": role,
        "exp": int((utc_now + timedelta(days=refresh_expire_days)).timestamp()),
        "iat": int(utc_now.timestamp()),
        "jti": jti_refresh,
        "type": "refresh",
    }
    refresh_token = jwt.encode(refresh_payload, secret_key, algorithm=algorithm)

    return access_token, refresh_token


def decode_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
    expected_type: str = "access",
) -> dict:
    """Decodes and validates a JWT token. Raises UnauthorizedException on failure."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        if payload.get("type") != expected_type or payload.get("sub") is None:
            raise UnauthorizedException("Invalid token type or missing subject")
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token has expired")
    except jwt.PyJWTError:
        raise UnauthorizedException("Could not validate credentials")


# ──────────────────────────────────────────────────────────────────────────────
# Token Revocation (Redis-backed blacklist)
# ──────────────────────────────────────────────────────────────────────────────

async def revoke_token(redis_client, jti: str, ttl_seconds: int) -> None:
    """Adds a token JTI to the Redis blacklist with a TTL matching its remaining expiry."""
    await redis_client.set(f"token:revoked:{jti}", "1", ex=ttl_seconds)
    logger.info("Token revoked", jti=jti, ttl=ttl_seconds)


async def is_token_revoked(redis_client, jti: str) -> bool:
    """Checks if a token JTI has been revoked."""
    result = await redis_client.get(f"token:revoked:{jti}")
    return result is not None


# ──────────────────────────────────────────────────────────────────────────────
# Account Lockout (Redis-backed)
# ──────────────────────────────────────────────────────────────────────────────

LOCKOUT_THRESHOLD = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes


async def record_failed_login(redis_client, email: str) -> int:
    """Increments failed login counter for an email. Returns the new count."""
    key = f"lockout:{email}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, LOCKOUT_DURATION_SECONDS)
    logger.warn("Failed login recorded", email=email, attempt=count)
    return count


async def is_account_locked(redis_client, email: str) -> bool:
    """Checks if an account is locked out due to excessive failed login attempts."""
    key = f"lockout:{email}"
    count = await redis_client.get(key)
    if count is not None and int(count) >= LOCKOUT_THRESHOLD:
        return True
    return False


async def clear_failed_logins(redis_client, email: str) -> None:
    """Clears failed login counter on successful authentication."""
    await redis_client.delete(f"lockout:{email}")


# ──────────────────────────────────────────────────────────────────────────────
# RBAC: Role-Based Access Control Dependency
# ──────────────────────────────────────────────────────────────────────────────

class RoleChecker:
    """FastAPI dependency that verifies the caller has one of the allowed roles.

    Usage:
        @router.post("/products", dependencies=[Depends(RoleChecker(["admin", "merchant"]))])
        async def create_product(...):
            ...
    """

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, x_user_roles: str | None = Header(None, alias="X-User-Roles")) -> str:
        if not x_user_roles:
            raise ForbiddenException("Missing role information")
        # Roles may be comma-separated from the gateway
        user_roles = [r.strip() for r in x_user_roles.split(",")]
        if not any(role in self.allowed_roles for role in user_roles):
            logger.warn(
                "Unauthorized access attempt",
                user_roles=user_roles,
                required_roles=self.allowed_roles,
            )
            raise ForbiddenException("Insufficient permissions")
        return x_user_roles


# ──────────────────────────────────────────────────────────────────────────────
# Redis Rate Limiter Dependency
# ──────────────────────────────────────────────────────────────────────────────

class RateLimiter:
    """FastAPI dependency implementing a sliding-window rate limiter backed by Redis.

    Usage:
        @router.post("/login", dependencies=[Depends(RateLimiter(max_requests=10, window_seconds=60))])
        async def login(...):
            ...
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    async def __call__(self, request: Request) -> None:
        redis_client = getattr(request.app.state, "redis_client", None)
        if redis_client is None:
            return  # No Redis configured — skip rate limiting (e.g. in unit tests)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}:{request.url.path}"

        current_count = await redis_client.incr(key)
        if current_count == 1:
            await redis_client.expire(key, self.window_seconds)

        if current_count > self.max_requests:
            logger.warn(
                "Rate limit exceeded",
                client_ip=client_ip,
                path=request.url.path,
                count=current_count,
            )
            raise CloudScaleException(
                status_code=429,
                detail="Too many requests. Please try again later.",
            )


# ──────────────────────────────────────────────────────────────────────────────
# Security Headers Middleware (OWASP)
# ──────────────────────────────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects OWASP-recommended HTTP security headers into every response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        return response


# ──────────────────────────────────────────────────────────────────────────────
# Audit Logging Helpers
# ──────────────────────────────────────────────────────────────────────────────

def audit_log(
    event_name: str,
    user_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    **extra,
) -> None:
    """Emits a structured audit log entry for security-critical events."""
    logger.info(
        event_name,
        audit=True,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
        **extra,
    )
