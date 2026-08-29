"""
Central application configuration.

Everything environment-specific (DB, JWT, storage, thresholds, CORS) is read
from environment variables so nothing environment-specific is hard-coded in
business logic. See .env.example for the full list of supported variables.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    APP_NAME: str = "Kaagaz2Code Backend"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+psycopg2://kaagaz2code:kaagaz2code@localhost:5432/kaagaz2code"
    )

    # --- JWT / Auth ---
    JWT_SECRET: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Object Storage (S3-compatible; MinIO locally, e.g. S3/R2/GCS in prod) ---
    OBJECT_STORAGE_ENDPOINT: str = "http://localhost:9000"
    OBJECT_STORAGE_ACCESS_KEY: str = "minioadmin"
    OBJECT_STORAGE_SECRET_KEY: str = "minioadmin"
    OBJECT_STORAGE_BUCKET: str = "kaagaz2code-documents"
    OBJECT_STORAGE_REGION: str = "us-east-1"
    OBJECT_STORAGE_USE_SSL: bool = False

    # --- OCR provider (pluggable) ---
    OCR_PROVIDER: str = "mock"  # mock | tesseract | google_vision | azure_ocr ...

    # --- AI extraction provider (pluggable) ---
    AI_PROVIDER: str = "mock"  # mock | anthropic | openai ...
    ANTHROPIC_API_KEY: str = ""

    # --- Auto-approval decision thresholds (configurable, not hard-coded) ---
    MIN_FIELD_CONFIDENCE: float = 0.85
    MIN_CRITICAL_FIELD_CONFIDENCE: float = 0.90
    # Stored as comma-separated strings (not List[str]) so plain env vars /
    # .env values work without needing JSON-encoded arrays. Use the `_list`
    # properties below to consume these as Python lists.
    CRITICAL_FIELDS: str = "owner_name,survey_number,khata_number,village"
    MAX_ACCEPTABLE_DISCREPANCY_SEVERITY: str = "LOW"  # LOW | MEDIUM | HIGH | CRITICAL

    # --- File upload limits ---
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_UPLOAD_EXTENSIONS: str = ".pdf,.png,.jpg,.jpeg,.tiff,.tif"
    ALLOWED_UPLOAD_MIME_TYPES: str = "application/pdf,image/png,image/jpeg,image/tiff"

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @staticmethod
    def _csv(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def critical_fields_list(self) -> list[str]:
        return self._csv(self.CRITICAL_FIELDS)

    @property
    def allowed_upload_extensions_list(self) -> list[str]:
        return self._csv(self.ALLOWED_UPLOAD_EXTENSIONS)

    @property
    def allowed_upload_mime_types_list(self) -> list[str]:
        return self._csv(self.ALLOWED_UPLOAD_MIME_TYPES)

    @property
    def cors_origins_list(self) -> list[str]:
        return self._csv(self.CORS_ORIGINS)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — import this, not Settings() directly."""
    return Settings()


settings = get_settings()
