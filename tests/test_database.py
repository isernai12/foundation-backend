from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import engine, get_db, check_db_health


def test_engine_configuration():
    assert engine is not None
    assert engine.pool is not None


def test_check_db_health():
    result = check_db_health()
    assert isinstance(result, dict)
    assert result["status"] == "ok"
    assert result["database"] == "connected"


def test_get_db_session_lifecycle():
    db_gen = get_db()
    session = next(db_gen)
    try:
        assert isinstance(session, Session)
        # Execute harmless read-only query
        result = session.execute(text("SELECT 1 AS test_val")).scalar()
        assert result == 1
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
