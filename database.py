"""Database configuration and session management."""
# SQLAlchemy setup - pretty standard boilerplate
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# SQLAlchemy engine with connection pooling
# pool_pre_ping checks connection health before using it
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # helps catch dead connections
    pool_size=10,
    max_overflow=20
)

# Session factory - creates new DB sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


def get_db():
    """FastAPI dependency - yields a DB session for each request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # always cleanup, even if something crashes
