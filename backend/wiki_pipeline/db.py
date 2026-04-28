"""Shared DB session factory for the wiki pipeline.

Adds the `backend/` directory to sys.path so `app.models.*` is importable
both when running as a package (e.g. via FastAPI) and when invoked as a
script (e.g. from Airflow workers or pytest).
"""
import os
import sys
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://user01:dkagh12%23@localhost:3306/llmwiki",
)

# 한글 문자열이 깨지지 않도록 charset=utf8mb4 보장
if "charset=" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL + ("&" if "?" in DATABASE_URL else "?") + "charset=utf8mb4"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a SQLAlchemy session; commit on success, rollback on error."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
