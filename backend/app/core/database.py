from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _ensure_utf8(url: str) -> str:
    """Make sure pymysql connects with charset=utf8mb4 so Korean text round-trips correctly."""
    if "charset=" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}charset=utf8mb4"


engine = create_engine(_ensure_utf8(settings.DATABASE_URL), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
