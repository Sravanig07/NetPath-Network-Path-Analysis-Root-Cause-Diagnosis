from __future__ import annotations

import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from backend.app.config import settings
from backend.app.models.base import Base

logger = logging.getLogger("netpath.database")

# Connect args for SQLite if needed
connect_args = {}
database_url = settings.DATABASE_URL

if database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

try:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        echo=settings.SQL_ECHO,
        connect_args=connect_args
    )
    # Test connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info(f"Connected successfully to database: {database_url.split('@')[-1] if '@' in database_url else database_url}")
except Exception as e:
    logger.warning(f"Could not connect to {database_url} ({e}). Falling back to local SQLite engine.")
    database_url = "sqlite:///./netpath.db"
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        echo=settings.SQL_ECHO,
        connect_args=connect_args
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully.")


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing a transactional database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
