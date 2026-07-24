from contextlib import asynccontextmanager

import structlog
from app.config import settings
from app.router import router
from cloudscale_shared import (
    CorrelationIdMiddleware,
    SecurityHeadersMiddleware,
    TenantContextMiddleware,
    init_db,
    init_redis,
    register_health_routes,
    setup_exception_handlers,
    setup_logging,
    setup_metrics,
    setup_tracing,
)
from fastapi import FastAPI

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.SERVICE_NAME)
    setup_tracing(settings.SERVICE_NAME)

    init_db(settings.DATABASE_URL)
    init_redis(settings.REDIS_URL)

    import os

    if os.getenv("RUN_MIGRATIONS", "false").lower() == "true":
        logger.info("Running database migrations via Alembic...")
        import asyncio

        from alembic import command
        from alembic.config import Config

        loop = asyncio.get_event_loop()

        def run_alembic():
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")

        await loop.run_in_executor(None, run_alembic)
        logger.info("Database migrations applied successfully.")
    else:
        logger.info("Database migration check skipped (RUN_MIGRATIONS=false).")

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
