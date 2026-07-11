from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "payment-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/payment_db"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    INVENTORY_EVENTS_TOPIC: str = "inventory-events"
    PAYMENT_EVENTS_TOPIC: str = "payment-events"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
