import os
from typing import List, Union, Optional
from urllib.parse import urlsplit
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("backend/.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General
    APP_NAME: str = "Foundation API"
    ENVIRONMENT: str = "development"  # development, staging, production, test
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1"

    # Security & JWT
    SECRET_KEY: str = "super-secret-foundation-backend-key-change-in-production-min-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day (standard)
    REMEMBER_ME_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    SESSION_COOKIE_NAME: str = "foundation_session"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://user:password@localhost:5432/foundation_db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 300  # 5 minutes, recommended for serverless/pooled PG (Neon)

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # Cloudinary CDN Configuration
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    CLOUDINARY_URL: Optional[str] = None
    CLOUDINARY_FOLDER: str = "foundation-erp"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            if not v.startswith("["):
                return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def sqlalchemy_database_url(self) -> str:
        """
        Normalize database URL for SQLAlchemy 2.0 with the psycopg3 driver.
        Converts 'postgresql://' or 'postgres://' to 'postgresql+psycopg://'.
        """
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @property
    def safe_database_display(self) -> str:
        """
        Return a sanitized connection string for logging/diagnostics without exposing passwords or tokens.
        """
        try:
            parsed = urlsplit(self.DATABASE_URL)
            hostname = parsed.hostname or "unknown"
            port = f":{parsed.port}" if parsed.port else ""
            path = parsed.path or ""
            return f"postgresql://***:***@{hostname}{port}{path}"
        except Exception:
            return "postgresql://***:***@host/db"


settings = Settings()
