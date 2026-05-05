from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

from cloudscale_shared import (
    setup_logging,
    setup_tracing,
    CorrelationIdMiddleware,
    TenantContextMiddleware,
    init_db,
    init_redis,
    setup_exception_handlers,
    setup_metrics,
    SecurityHeadersMiddleware,
    register_health_routes,
)
from app.config import settings
from app.router import router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.SERVICE_NAME)
    setup_tracing(settings.SERVICE_NAME)

    init_db(settings.DATABASE_URL)
    init_redis(settings.REDIS_URL)

    from app.models import Base
    from cloudscale_shared.database import db_manager

    if db_manager:
        async with db_manager._write_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")

    logger.info("Catalog microservice initialized", service_name=settings.SERVICE_NAME)
    yield

    from cloudscale_shared.database import db_manager, redis_manager

    if db_manager:
        await db_manager.close()
    if redis_manager:
        await redis_manager.close()
    logger.info("Catalog microservice shutdown finished.")


app = FastAPI(
    title="CloudScale Commerce - Catalog Service",
    description="Microservice managing catalog items, search, and dynamic cache-aside fetching.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(CorrelationIdMiddleware)
setup_exception_handlers(app)
setup_metrics(app, settings.SERVICE_NAME)
register_health_routes(app, settings.SERVICE_NAME)
app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.SERVICE_NAME}
