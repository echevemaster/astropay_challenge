"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings


def _get_engine_kwargs():
    """Get engine kwargs based on database type."""
    kwargs = {}
    
    # SQLite doesn't support pool parameters
    if settings.database_url.startswith("sqlite"):
        kwargs = {
            "connect_args": {"check_same_thread": False},
            "pool_pre_ping": False,
        }
    else:
        # PostgreSQL and other databases support pool parameters
        kwargs = {
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 3600,
        }
    
    return kwargs


engine = create_engine(
    settings.database_url,
    **_get_engine_kwargs()
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

