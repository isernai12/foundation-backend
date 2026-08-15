import os
from app.core.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.APP_NAME == "Foundation API"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.HOST == "0.0.0.0"
    assert settings.PORT == 8000


def test_settings_robust_with_empty_strings():
    settings = Settings(PORT="", DEBUG="", DATABASE_URL="")
    assert settings.PORT == 8000
    assert settings.DEBUG is False
    assert settings.sqlalchemy_database_url.startswith("postgresql+psycopg://")


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

    # Quoted string in double quotes
    url4 = '"postgresql://user:pass@host:5432/db"'
    settings4 = Settings(DATABASE_URL=url4)
    assert settings4.sqlalchemy_database_url.startswith("postgresql+psycopg://")
    assert '"' not in settings4.sqlalchemy_database_url

    # Quoted string in single quotes
    url5 = "'postgresql+psycopg2://user:pass@host:5432/db'"
    settings5 = Settings(DATABASE_URL=url5)
    assert settings5.sqlalchemy_database_url.startswith("postgresql+psycopg://")
    assert "'" not in settings5.sqlalchemy_database_url

    # postgresql+psycopg2 -> postgresql+psycopg
    url6 = "postgresql+psycopg2://user:pass@host:5432/db"
    settings6 = Settings(DATABASE_URL=url6)
    assert settings6.sqlalchemy_database_url == "postgresql+psycopg://user:pass@host:5432/db"
