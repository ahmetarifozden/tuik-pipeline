from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

DB_URL = os.getenv("DATABASE_URI") or os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URI or DATABASE_URL is not set")

print("DB_URL_IN_APP =", DB_URL)

engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
