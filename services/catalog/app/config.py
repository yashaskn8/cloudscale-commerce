from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "catalog-service"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/catalog_db"
    REDIS_URL: str = "redis://localhost:6379/1"  # Using db 1 for catalog cache

    PRODUCT_CACHE_TTL_SECONDS: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
