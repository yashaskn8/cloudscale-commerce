"""Auth Service — API Router (Phase 4 Hardened).

Exposes endpoints for:
- User registration (with password policy)
- Login (with lockout detection and audit logging)
- Token refresh (rotation with old-token revocation)
- Logout (access token revocation)
- Current user profile retrieval
- Admin user listing (RBAC-protected)
"""
import structlog
from app.models import User
from app.schemas import RefreshRequest, TokenResponse, UserLogin, UserRegister, UserResponse
from app.service import AuthService
from cloudscale_shared import get_db_session
from cloudscale_shared.query import Page, PageParams
from cloudscale_shared.security import RateLimiter, RoleChecker
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_auth_service(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> AuthService:
    """FastAPI dependency injection for AuthService with Redis client."""
    redis_client = getattr(request.app.state, "redis_client", None)
    return AuthService(db, redis_client=redis_client)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service),
) -> User:
    """Dependency that validates JWT (including revocation) and returns the user."""
    return await service.get_current_user_from_token(token)


# ── Registration ──────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister,
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Register a new user account with password policy enforcement."""
    user = await service.register_user(payload)
    return UserResponse.model_validate(user)


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(RateLimiter(max_requests=10, window_seconds=60))],
)
async def login(
    payload: UserLogin,
    request: Request,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate a user with lockout protection and return JWT tokens."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    return await service.authenticate_user(payload, ip_address=ip, user_agent=ua)


# ── Token Refresh ─────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    payload: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Rotate tokens: validate refresh token, revoke old, issue new pair."""
    return await service.refresh_tokens(payload.refresh_token)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: str = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service),
) -> None:
    """Revoke the current access token."""
    await service.logout(token)


# ── Current User ──────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Retrieve the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


# ── Admin: User Listing (RBAC) ───────────────────────────────────────────────

@router.get(
    "/users",
    response_model=Page[UserResponse],
    dependencies=[Depends(RoleChecker(["admin"]))],
)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    service: AuthService = Depends(get_auth_service),
) -> Page[UserResponse]:
    """List all users (admin only)."""
    params = PageParams(page=page, size=size)
    return await service.list_users(params)
