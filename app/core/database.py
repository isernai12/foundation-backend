import logging
from typing import Generator, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy 2.0 Engine with connection pooling
engine = create_engine(
    settings.sqlalchemy_database_url,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    future=True,
)

# Session factory bound to engine
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session per request.
    Closes the session cleanly upon completion.
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_health() -> Dict[str, Any]:
    """
    Executes a harmless read-only query (SELECT 1) to verify database connectivity.
    Guarantees no internal credentials, passwords, or tokens are leaked in the output.
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1 AS healthy;"))
            row = result.mappings().one()
            if row.get("healthy") == 1:
                return {
                    "status": "ok",
                    "database": "connected",
                }
            return {
                "status": "error",
                "database": "unexpected_result",
            }
    except SQLAlchemyError as err:
        logger.error(f"Database health check failed: {type(err).__name__}")
        return {
            "status": "error",
            "database": "disconnected",
            "detail": "Database connection failed",
        }
    except Exception as err:
        logger.error(f"Unexpected error during database health check: {type(err).__name__}")
        return {
            "status": "error",
            "database": "unavailable",
            "detail": "Service temporarily unavailable",
        }
