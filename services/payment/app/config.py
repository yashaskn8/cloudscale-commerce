from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "payment-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/payment_db"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    STRIPE_WEBHOOK_SECRET: str  # REQUIRED — must be set via env var or .env file
    SIMULATE_PAYMENTS: bool = True  # Set False in production to use real Stripe charges

    INVENTORY_EVENTS_TOPIC: str = "inventory-events"
    PAYMENT_EVENTS_TOPIC: str = "payment-events"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
