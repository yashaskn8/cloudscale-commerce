from contextlib import asynccontextmanager

import structlog
from app.config import settings
from app.consumers import init_kafka, shutdown_kafka
from cloudscale_shared import (
    CorrelationIdMiddleware,
    SecurityHeadersMiddleware,
    TenantContextMiddleware,
    init_db,
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

    import os
    if os.getenv("RUN_MIGRATIONS", "false").lower() == "true":
        from app.models import Base
        from cloudscale_shared.database import db_manager
        if db_manager:
            async with db_manager._write_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized successfully.")
    else:
        logger.info("Database initialization skipped (RUN_MIGRATIONS=false).")

    try:
        await init_kafka()
    except Exception as e:
        logger.error("Failed to start Kafka listeners.", error=str(e))

    logger.info("Payment microservice initialized", service_name=settings.SERVICE_NAME)
    yield

    await shutdown_kafka()
    from cloudscale_shared.database import db_manager

    if db_manager:
        await db_manager.close()
    logger.info("Payment microservice shutdown finished.")


app = FastAPI(
    title="CloudScale Commerce - Payment Service",
    description="Event-driven Payment Service checking order credit charges and mock processing.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(CorrelationIdMiddleware)
from app.router import router as billing_router

setup_exception_handlers(app)
setup_metrics(app, settings.SERVICE_NAME)
register_health_routes(app, settings.SERVICE_NAME, kafka_bootstrap=settings.KAFKA_BOOTSTRAP_SERVERS)
app.include_router(billing_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.SERVICE_NAME}
