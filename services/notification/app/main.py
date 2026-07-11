from contextlib import asynccontextmanager

import structlog
from app.config import settings
from app.consumers import init_kafka, shutdown_kafka
from cloudscale_shared import (
    CorrelationIdMiddleware,
    SecurityHeadersMiddleware,
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
    # Initialize logging
    setup_logging(settings.SERVICE_NAME)
    setup_tracing(settings.SERVICE_NAME)

    # Initialize Database for Inbox tracking
    init_db(settings.DATABASE_URL)

    # Create DB schemas automatically
    from app.models import Base
    from cloudscale_shared.database import db_manager

    if db_manager:
        async with db_manager._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully.")

    # Initialize Kafka consumer loop
    try:
        await init_kafka()
    except Exception as e:
        logger.error("Failed to start Kafka listeners.", error=str(e))

    logger.info("Notification microservice initialized", service_name=settings.SERVICE_NAME)
    yield

    # Clean up
    await shutdown_kafka()
    from cloudscale_shared.database import db_manager

    if db_manager:
        await db_manager.close()
    logger.info("Notification microservice shutdown finished.")


app = FastAPI(
    title="CloudScale Commerce - Notification Service",
    description="Stateless Event-driven Notification Service that triggers client emails and SMS.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIdMiddleware)
setup_exception_handlers(app)
setup_metrics(app, settings.SERVICE_NAME)
register_health_routes(app, settings.SERVICE_NAME, kafka_bootstrap=settings.KAFKA_BOOTSTRAP_SERVERS)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.SERVICE_NAME}
