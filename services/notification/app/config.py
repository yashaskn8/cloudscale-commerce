from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SERVICE_NAME: str = "notification-service"
    DATABASE_URL: str = "sqlite+aiosqlite:///notification_inbox.db"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    
    PAYMENT_EVENTS_TOPIC: str = "payment-events"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
