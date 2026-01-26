"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from config import settings

# Create database engine with connection pooling
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before use
    pool_size=5,
    max_overflow=10,
    echo=False  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for non-FastAPI usage (scripts, tests).

    Usage:
        with get_db_session() as db:
            db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
