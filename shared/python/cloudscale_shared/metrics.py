"""Production-Grade Metrics & Health Check Module.

Provides:
- RED metrics (Rate, Errors, Duration) via Prometheus middleware
- Custom business metric registries
- Database & Redis connection pool gauges
- Standardized liveness/readiness health probe endpoints
"""

import time

import structlog
from fastapi import FastAPI, Request
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

logger = structlog.get_logger()

# ──────────────────────────────────────────────────────────────────────────────
# RED Metrics (Rate, Errors, Duration)
# ──────────────────────────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["service", "method", "endpoint", "http_status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP Request Latency in seconds",
    ["service", "method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
REQUEST_ERRORS = Counter(
    "http_request_errors_total",
    "Total HTTP 5xx Errors",
    ["service", "method", "endpoint"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Custom Business Metrics
# ──────────────────────────────────────────────────────────────────────────────

ORDERS_CREATED = Counter("orders_created_total", "Total orders created", ["service"])
PAYMENTS_PROCESSED = Counter("payments_processed_total", "Total payments processed", ["service", "status"])
INVENTORY_RESERVATIONS = Counter("inventory_reservations_total", "Total inventory reservations", ["service", "status"])
NOTIFICATIONS_SENT = Counter("notifications_sent_total", "Total notifications sent", ["service"])

# ──────────────────────────────────────────────────────────────────────────────
# Infrastructure Gauges
# ──────────────────────────────────────────────────────────────────────────────

DB_POOL_SIZE = Gauge("db_connection_pool_size", "Current DB connection pool size", ["service"])
DB_POOL_CHECKED_OUT = Gauge("db_connections_checked_out", "DB connections currently checked out", ["service"])
REDIS_CONNECTED = Gauge("redis_connected", "Whether Redis is connected (1=yes, 0=no)", ["service"])


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking request counts, latencies, and 5xx errors."""

    def __init__(self, app: FastAPI, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        endpoint = request.url.path
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time
            status_code = str(response.status_code)

            REQUEST_COUNT.labels(
                service=self.service_name,
                method=method,
                endpoint=endpoint,
                http_status=status_code,
            ).inc()
            REQUEST_LATENCY.labels(
                service=self.service_name,
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            if response.status_code >= 500:
                REQUEST_ERRORS.labels(
                    service=self.service_name,
                    method=method,
                    endpoint=endpoint,
                ).inc()

            return response
        except Exception:
            duration = time.perf_counter() - start_time
            REQUEST_COUNT.labels(
                service=self.service_name,
                method=method,
                endpoint=endpoint,
                http_status="500",
            ).inc()
            REQUEST_LATENCY.labels(
                service=self.service_name,
                method=method,
                endpoint=endpoint,
            ).observe(duration)
            REQUEST_ERRORS.labels(
                service=self.service_name,
                method=method,
                endpoint=endpoint,
            ).inc()
            raise


# ──────────────────────────────────────────────────────────────────────────────
# Health Probes
# ──────────────────────────────────────────────────────────────────────────────


async def check_db_health() -> dict:
    """Checks PostgreSQL connectivity via the global db_manager."""
    try:
        from cloudscale_shared.database import db_manager

        if db_manager is None:
            return {"postgres": "not_configured"}
        async with db_manager.session() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"postgres": "healthy"}
    except Exception as exc:
        return {"postgres": f"unhealthy: {exc}"}


async def check_redis_health() -> dict:
    """Checks Redis connectivity via the global redis_manager."""
    try:
        from cloudscale_shared.database import redis_manager

        if redis_manager is None:
            return {"redis": "not_configured"}
        client = redis_manager.get_client()
        await client.ping()
        await client.aclose()
        return {"redis": "healthy"}
    except Exception as exc:
        return {"redis": f"unhealthy: {exc}"}


async def check_kafka_health(bootstrap_servers: str) -> dict:
    """Checks Kafka broker connectivity via a lightweight socket probe."""
    import asyncio

    try:
        host, port_str = bootstrap_servers.split(",")[0].split(":")
        port = int(port_str)
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=3.0)
        writer.close()
        await writer.wait_closed()
        return {"kafka": "healthy"}
    except Exception as exc:
        return {"kafka": f"unhealthy: {exc}"}


def register_health_routes(
    app: FastAPI,
    service_name: str,
    kafka_bootstrap: str | None = None,
) -> None:
    """Registers /health/liveness and /health/readiness endpoints on the app."""

    @app.get("/health/liveness", tags=["Health"])
    async def liveness():
        return {"status": "alive", "service": service_name}

    @app.get("/health/readiness", tags=["Health"])
    async def readiness():
        checks: dict = {}
        db_status = await check_db_health()
        checks.update(db_status)

        redis_status = await check_redis_health()
        checks.update(redis_status)

        if kafka_bootstrap:
            kafka_status = await check_kafka_health(kafka_bootstrap)
            checks.update(kafka_status)

        all_healthy = all(v == "healthy" or v == "not_configured" for v in checks.values())
        status_code = 200 if all_healthy else 503
        return JSONResponse(
            content={"status": "ready" if all_healthy else "not_ready", "checks": checks},
            status_code=status_code,
        )


def setup_metrics(app: FastAPI, service_name: str) -> None:
    """Configures Prometheus ASGI metrics page and tracks HTTP requests."""
    app.add_middleware(PrometheusMiddleware, service_name=service_name)
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
