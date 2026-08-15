from typing import Optional, Any
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

    # Server & Port Binding (0.0.0.0 binding for container / cloud hosting like Render)
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Cloudinary CDN Configuration
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    CLOUDINARY_URL: Optional[str] = None
    CLOUDINARY_FOLDER: str = "foundation-erp"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            if not v.startswith("["):
                return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i).strip() for i in v if str(i).strip()]
        return ["*"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def clean_database_url(cls, v: Any) -> str:
        """
        Sanitize raw database URL from environment or .env:
        Strips surrounding quotes (single, double, backtick) and whitespace.
        """
        if v is None:
            return "postgresql+psycopg://user:password@localhost:5432/foundation_db"
        val = str(v).strip()
        while len(val) >= 2 and (
            (val[0] == '"' and val[-1] == '"')
            or (val[0] == "'" and val[-1] == "'")
            or (val[0] == "`" and val[-1] == "`")
        ):
            val = val[1:-1].strip()
        val = val.strip("'\" \t\r\n")
        return val or "postgresql+psycopg://user:password@localhost:5432/foundation_db"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def sqlalchemy_database_url(self) -> str:
        """
        Normalize database URL for SQLAlchemy 2.0 with the psycopg3 driver.
        Handles surrounding quotes, whitespace, legacy 'postgres://', 'postgresql://',
        'postgresql+psycopg2://', and variations to ensure standard 'postgresql+psycopg://'.
        """
        url = str(self.DATABASE_URL or "").strip()
        while len(url) >= 2 and (
            (url[0] == '"' and url[-1] == '"')
            or (url[0] == "'" and url[-1] == "'")
            or (url[0] == "`" and url[-1] == "`")
        ):
            url = url[1:-1].strip()
        url = url.strip("'\" \t\r\n")

        prefixes = [
            ("postgresql+psycopg2://", "postgresql+psycopg://"),
            ("postgresql+psycopg3://", "postgresql+psycopg://"),
            ("postgres+psycopg2://", "postgresql+psycopg://"),
            ("postgres+psycopg://", "postgresql+psycopg://"),
            ("postgres://", "postgresql+psycopg://"),
            ("postgresql://", "postgresql+psycopg://"),
        ]
        matched = False
        for old_prefix, new_prefix in prefixes:
            if url.startswith(old_prefix):
                url = new_prefix + url[len(old_prefix):]
                matched = True
                break

        if not matched and not url.startswith("postgresql+psycopg://") and "://" in url:
            scheme, rest = url.split("://", 1)
            if scheme.startswith("postgres"):
                url = f"postgresql+psycopg://{rest}"

        return url

    @property
    def safe_database_display(self) -> str:
        """
        Return a sanitized connection string for logging/diagnostics without exposing passwords or tokens.
        """
        try:
            url = str(self.DATABASE_URL or "").strip()
            while len(url) >= 2 and (
                (url[0] == '"' and url[-1] == '"')
                or (url[0] == "'" and url[-1] == "'")
                or (url[0] == "`" and url[-1] == "`")
            ):
                url = url[1:-1].strip()
            url = url.strip("'\" \t\r\n")
            parsed = urlsplit(url)
            hostname = parsed.hostname or "unknown"
            port = f":{parsed.port}" if parsed.port else ""
            path = parsed.path or ""
            return f"postgresql://***:***@{hostname}{port}{path}"
        except Exception:
            return "postgresql://***:***@host/db"


settings = Settings()
