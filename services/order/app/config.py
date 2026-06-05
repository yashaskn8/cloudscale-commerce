from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SERVICE_NAME: str = "order-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/order_db"
    REDIS_URL: str = "redis://localhost:6379/3" # Using db 3 for order idempotency tracking
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    
    ORDER_EVENTS_TOPIC: str = "order-events"
    INVENTORY_EVENTS_TOPIC: str = "inventory-events"
    PAYMENT_EVENTS_TOPIC: str = "payment-events"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
