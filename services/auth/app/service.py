"""Auth Service — Application Service Layer (Phase 4 Hardened).

Implements:
- Argon2id password hashing with legacy bcrypt migration
- JWT access/refresh token lifecycle with Redis-backed revocation
- Account lockout after N failed attempts
- Password policy enforcement
- Structured audit logging for security events
"""
import uuid
from datetime import UTC, datetime

import structlog
from app.config import settings
from app.models import User
from app.repository import UserRepository
from app.schemas import TokenResponse, UserLogin, UserRegister, UserResponse
from cloudscale_shared import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from cloudscale_shared.query import Page, PageParams
from cloudscale_shared.security import (
    audit_log,
    clear_failed_logins,
    create_token_pair,
    decode_token,
    hash_password,
    is_account_locked,
    is_token_revoked,
    password_needs_rehash,
    record_failed_login,
    revoke_token,
    validate_password_policy,
    verify_password,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()


class AuthService:
    """Service layer handling authentication with production-grade security."""

    def __init__(self, session: AsyncSession, redis_client=None):
        self.repo = UserRepository(session)
        self.session = session
        self.redis = redis_client

    # ── Registration ──────────────────────────────────────────────────────

    async def register_user(self, payload: UserRegister) -> User:
        """Registers a new user with password policy validation and Argon2id hashing."""
        # Password policy enforcement
        violations = validate_password_policy(payload.password)
        if violations:
            raise ValidationException("; ".join(violations))

        if await self.repo.exists_by_email(payload.email):
            logger.warn("Registration failed — email exists", email=payload.email)
            raise ConflictException("Email already registered")

        new_user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            first_name=payload.first_name,
            last_name=payload.last_name,
            role="shopper",
        )
        await self.repo.add(new_user)
        await self.session.flush()

        audit_log("UserRegistered", user_id=str(new_user.id))
        return new_user

    # ── Authentication ────────────────────────────────────────────────────

    async def authenticate_user(
        self, payload: UserLogin, ip_address: str | None = None, user_agent: str | None = None
    ) -> TokenResponse:
        """Authenticates credentials with lockout protection and audit logging."""
        # Account lockout check
        if self.redis and await is_account_locked(self.redis, payload.email):
            audit_log(
                "AccountLockedLoginAttempt",
                ip_address=ip_address,
                user_agent=user_agent,
                email=payload.email,
            )
            raise UnauthorizedException(
                "Account temporarily locked due to too many failed attempts. Try again later."
            )

        user = await self.repo.get_by_email(payload.email)

        if not user or not verify_password(payload.password, user.password_hash):
            # Record failed attempt
            if self.redis:
                await record_failed_login(self.redis, payload.email)
            audit_log(
                "UserLoginFailed",
                ip_address=ip_address,
                user_agent=user_agent,
                email=payload.email,
            )
            raise UnauthorizedException("Incorrect email or password")

        # Successful login — clear lockout counter
        if self.redis:
            await clear_failed_logins(self.redis, payload.email)

        # Transparent rehash if using legacy bcrypt
        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(payload.password)
            await self.session.flush()
            logger.info("Password rehashed to Argon2id", user_id=str(user.id))

        access_token, refresh_token = create_token_pair(
            user_id=str(user.id),
            role=user.role,
            secret_key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
            access_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            refresh_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
        )

        audit_log(
            "UserLoginSuccess",
            user_id=str(user.id),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    # ── Token Rotation ────────────────────────────────────────────────────

    async def refresh_tokens(self, refresh_token_str: str) -> TokenResponse:
        """Rotates tokens: validates the refresh token, revokes the old one, issues new pair."""
        payload = decode_token(
            refresh_token_str,
            settings.JWT_SECRET_KEY,
            settings.JWT_ALGORITHM,
            expected_type="refresh",
        )
        jti = payload.get("jti")

        # Check if the refresh token has been revoked
        if self.redis and jti and await is_token_revoked(self.redis, jti):
            audit_log("RevokedRefreshTokenUsed", user_id=payload.get("sub"), jti=jti)
            raise UnauthorizedException("Refresh token has been revoked")

        # Revoke the old refresh token
        if self.redis and jti:
            exp = payload.get("exp", 0)
            ttl = max(exp - int(datetime.now(UTC).timestamp()), 1)
            await revoke_token(self.redis, jti, ttl)

        # Issue fresh token pair
        access_token, new_refresh = create_token_pair(
            user_id=payload["sub"],
            role=payload.get("role", "shopper"),
            secret_key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
            access_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            refresh_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
        )

        audit_log("TokenRotated", user_id=payload["sub"])
        return TokenResponse(access_token=access_token, refresh_token=new_refresh)

    # ── Logout (Token Revocation) ─────────────────────────────────────────

    async def logout(self, access_token_str: str) -> None:
        """Revokes the current access token by blacklisting its JTI in Redis."""
        payload = decode_token(
            access_token_str,
            settings.JWT_SECRET_KEY,
            settings.JWT_ALGORITHM,
            expected_type="access",
        )
        jti = payload.get("jti")
        if self.redis and jti:
            exp = payload.get("exp", 0)
            ttl = max(exp - int(datetime.now(UTC).timestamp()), 1)
            await revoke_token(self.redis, jti, ttl)

        audit_log("UserLogout", user_id=payload.get("sub"))

    # ── User Retrieval ────────────────────────────────────────────────────

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """Retrieves a user by their ID."""
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        return user

    async def get_current_user_from_token(self, token: str) -> User:
        """Validates an access token (including revocation check) and returns the User."""
        payload = decode_token(
            token, settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM, expected_type="access"
        )
        jti = payload.get("jti")
        if self.redis and jti and await is_token_revoked(self.redis, jti):
            raise UnauthorizedException("Token has been revoked")

        user_uuid = uuid.UUID(payload["sub"])
        return await self.get_user_by_id(user_uuid)

    async def list_users(self, params: PageParams) -> Page[UserResponse]:
        """Returns a paginated list of users."""
        items, total = await self.repo.list_paginated(params)
        user_responses = [UserResponse.model_validate(u) for u in items]
        return Page.create(user_responses, total, params)
