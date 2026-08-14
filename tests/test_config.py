import os
from backend.app.core.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.APP_NAME == "Foundation API"
    assert settings.API_V1_STR == "/api/v1"
    assert isinstance(settings.CORS_ORIGINS, list)


def test_safe_database_display_masks_credentials():
    secret_url = "postgresql://myuser:super_secret_password@db.example.com:5432/proddb?sslmode=require"
    settings = Settings(DATABASE_URL=secret_url)
    display = settings.safe_database_display
    assert "super_secret_password" not in display
    assert "myuser" not in display
    assert "db.example.com" in display
    assert display.startswith("postgresql://***:***@")


def test_sqlalchemy_database_url_normalization():
    # Standard postgresql -> postgresql+psycopg
    url1 = "postgresql://user:pass@host:5432/db"
    settings1 = Settings(DATABASE_URL=url1)
    assert settings1.sqlalchemy_database_url.startswith("postgresql+psycopg://")

    # postgres:// legacy -> postgresql+psycopg
    url2 = "postgres://user:pass@host:5432/db"
    settings2 = Settings(DATABASE_URL=url2)
    assert settings2.sqlalchemy_database_url.startswith("postgresql+psycopg://")

    # Already prefixed -> untouched
    url3 = "postgresql+psycopg://user:pass@host:5432/db"
    settings3 = Settings(DATABASE_URL=url3)
    assert settings3.sqlalchemy_database_url == url3


def test_cors_origins_parsing():
    settings = Settings(CORS_ORIGINS="http://localhost:3000, https://app.example.com")
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "https://app.example.com" in settings.CORS_ORIGINS
    assert len(settings.CORS_ORIGINS) == 2
