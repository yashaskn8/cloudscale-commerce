from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "order-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/order_db"
    REDIS_URL: str = "redis://localhost:6379/3"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    ORDER_EVENTS_TOPIC: str = "order-events"
    INVENTORY_EVENTS_TOPIC: str = "inventory-events"
    PAYMENT_EVENTS_TOPIC: str = "payment-events"

    # Saga Timeout & Sweeper Configuration
    SAGA_TIMEOUT_MINUTES: int = 15
    SAGA_SWEEP_INTERVAL_SECONDS: int = 60
    SAGA_SWEEP_BATCH_SIZE: int = 100

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
