from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "inventory-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/inventory_db"
    REDIS_URL: str = "redis://localhost:6379/2"  # Using db 2 for inventory locks
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    ORDER_EVENTS_TOPIC: str = "order-events"
    INVENTORY_EVENTS_TOPIC: str = "inventory-events"
    PAYMENT_EVENTS_TOPIC: str = "payment-events"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
