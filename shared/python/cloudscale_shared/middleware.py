import contextvars
import time
import uuid

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = structlog.get_logger()

# Thread-safe ContextVar to hold tenant context for SQL queries
tenant_id_context = contextvars.ContextVar("tenant_id", default="default-tenant")

def get_current_tenant() -> str:
    """Helper to retrieve the tenant ID associated with the current request context."""
    return tenant_id_context.get()

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts or generates a correlation ID for tracing distributed transactions."""
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("x-correlation-id")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            path=request.url.path,
            method=request.method,
            client_host=request.client.host if request.client else "unknown"
        )

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time
            logger.info("Request processed", status_code=response.status_code, duration_ms=round(duration * 1000, 2))
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        except Exception as exc:
            duration = time.perf_counter() - start_time
            logger.exception("Unhandled exception during request processing", error=str(exc), duration_ms=round(duration * 1000, 2))
            from fastapi.responses import JSONResponse
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error", "correlation_id": correlation_id}
            )
            response.headers["X-Correlation-ID"] = correlation_id
            return response

class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts the tenant context header and attaches it to request contextvars."""
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        tenant_id = request.headers.get("X-Tenant-ID") or request.headers.get("x-tenant-id") or "default-tenant"

        # Bind tenant context
        token = tenant_id_context.set(tenant_id)
        structlog.contextvars.bind_contextvars(tenant_id=tenant_id)

        try:
            response = await call_next(request)
            response.headers["X-Tenant-ID"] = tenant_id
            return response
        finally:
            tenant_id_context.reset(token)
