"""Shared helpers for Airflow DAGs in this project.

Adds the repo's `backend/` directory to sys.path so DAG tasks can import
`wiki_pipeline.*` and `app.models.*` regardless of where the Airflow
worker process started.
"""
from __future__ import annotations

import logging
import os
import sys
from functools import wraps

BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "backend")
)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://user01:dkagh12%23@localhost:3306/llmwiki",
)

logger = logging.getLogger("llmwiki.dags")


def mark_post_failed(post_id: int, error: str) -> None:
    """Set an ingest post's status to `failed` without raising on errors."""
    try:
        from app.models.ingest import IngestPost, IngestPostStatus
        from wiki_pipeline.db import SessionLocal

        session = SessionLocal()
        try:
            post = session.get(IngestPost, post_id)
            if post:
                post.status = IngestPostStatus.failed
                session.commit()
        finally:
            session.close()
    except Exception as e:
        logger.error("Failed to mark post %s as failed: %s", post_id, e)


def isolated_task(func):
    """Decorator: catches all task exceptions, logs them, returns False on failure.

    Lets a single failed task in a parallel/dynamic mapping not abort the run.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error("Task %s failed: %s", func.__name__, e, exc_info=True)
            return False

    return wrapper
