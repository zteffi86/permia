from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str

    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    AUTH_REQUIRED: bool = False  # Dev mode allows unauthenticated requests

    # Export signing keys
    EXPORT_PRIVATE_KEY_PATH: str = "./keys/export_private_key.pem"
    EXPORT_PUBLIC_KEY_PATH: str = "./keys/export_public_key.pem"

    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_STORAGE_CONTAINER_NAME: str = "evidence"
    AZURE_STORAGE_EXPORT_CONTAINER_NAME: str = "exports"
    STORAGE_PRESIGNED_URL_EXPIRY: int = 3600  # 1 hour in seconds

    # Application
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    API_VERSION: str = "v1"
    API_TITLE: str = "Permía API"
    API_DESCRIPTION: str = "Deterministic enforcement infrastructure for regulated industries"

    # Features
    ENABLE_DOCS: bool = True
    ENABLE_REDOC: bool = True
    ENABLE_EXPORT_API: bool = True

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Logging
    LOG_LEVEL: str = "INFO"

    # Monitoring
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # Evidence Validation (MVP Evidence Policy defaults)
    MAX_TIME_DRIFT_SECONDS: float = 30.0
    MIN_GPS_ACCURACY_METERS: float = 50.0
    REPLAY_WINDOW_DAYS: int = 30

    # Export Settings
    EXPORT_RETENTION_DAYS: int = 90
    EXPORT_STORAGE_PREFIX: str = "exports/"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
