
from __future__ import annotations
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

DB_URL = os.getenv("DATABASE_URL", "sqlite:///sma_av_ai_ops.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # <- important
)
@contextmanager
def get_session():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


