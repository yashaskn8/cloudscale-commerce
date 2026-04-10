from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SERVICE_NAME: str = "auth-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/auth_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    JWT_SECRET_KEY: str = "supersecretkeyforcloudscalecommercejwtissuancechangeinprod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    LOCKOUT_THRESHOLD: int = 5
    LOCKOUT_DURATION_SECONDS: int = 900

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
