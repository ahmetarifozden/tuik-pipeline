from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from typing import Generator

from src.tuik_pipeline.core.config import settings
from src.tuik_pipeline.core.logging import get_logger

logger = get_logger(__name__)

DB_URL = settings.database_url
if not DB_URL:
    logger.critical("DATABASE_URI or DATABASE_URL is not set in environment variables.")
    raise RuntimeError("DATABASE_URI or DATABASE_URL is not set")

# logger.info(f"Connecting to database: {DB_URL}") # Security: Avoid printing credentials

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db() -> Generator:
    """
    Dependency generator for FastAPI and scripts to get a DB session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
