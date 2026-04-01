from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

from cloudscale_shared import (
    setup_logging,
    setup_tracing,
    CorrelationIdMiddleware,
    init_db,
    init_redis,
    setup_exception_handlers,
    setup_metrics,
    SecurityHeadersMiddleware,
    register_health_routes,
)
from app.config import settings
from app.router import router
from app.consumers import init_kafka, shutdown_kafka

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
        async with db_manager._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")

    try:
        await init_kafka()
    except Exception as e:
        logger.error("Failed to start Kafka listeners.", error=str(e))

    logger.info("Inventory microservice initialized", service_name=settings.SERVICE_NAME)
    yield

    await shutdown_kafka()
    from cloudscale_shared.database import db_manager, redis_manager

    if db_manager:
        await db_manager.close()
    if redis_manager:
        await redis_manager.close()
    logger.info("Inventory microservice shutdown finished.")


app = FastAPI(
    title="CloudScale Commerce - Inventory Service",
    description="Microservice managing real-time stock levels, optimistic concurrency, and distributed locking.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIdMiddleware)
setup_exception_handlers(app)
setup_metrics(app, settings.SERVICE_NAME)
register_health_routes(app, settings.SERVICE_NAME, kafka_bootstrap=settings.KAFKA_BOOTSTRAP_SERVERS)
app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.SERVICE_NAME}
