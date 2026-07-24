from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "payment-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/payment_db"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    STRIPE_WEBHOOK_SECRET: str = "whsec_dev_test_secret_key"
    SIMULATE_PAYMENTS: bool = True  # Set False in production to use real Stripe charges

    INVENTORY_EVENTS_TOPIC: str = "inventory-events"
    PAYMENT_EVENTS_TOPIC: str = "payment-events"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
