from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVICE_NAME: str = "catalog-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/catalog_db"
    REDIS_URL: str = "redis://localhost:6379/1" # Using db 1 for catalog cache

    PRODUCT_CACHE_TTL_SECONDS: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
