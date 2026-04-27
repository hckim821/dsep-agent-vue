"""Daily ingest DAG: OCR pending posts, ingest into wiki, commit.

Flow (design spec 8.1):
    fetch_pending_posts
        -> ocr_images   (dynamic mapping, parallel per post)
        -> run_ingest   (sequential per post, race-condition safe)
        -> update_index_and_commit
        -> notify
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta

import pendulum
from airflow import DAG
from airflow.decorators import task

# Make wiki_pipeline + app.models importable from worker processes.
BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "backend")
)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

logger = logging.getLogger("llmwiki.ingest_daily")

default_args = {
    "owner": "llmwiki",
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="wiki_ingest_daily",
    default_args=default_args,
    description="Daily ingest: OCR + ingest pending posts into the wiki",
    schedule="0 2 * * *",
    start_date=pendulum.today("UTC").subtract(days=1),
    catchup=False,
    tags=["llmwiki", "ingest"],
    max_active_runs=1,
) as dag:

    @task
    def fetch_pending_posts() -> list[int]:
        """Return IDs of every post still in `pending` status, oldest first."""
        from app.models.ingest import IngestPost, IngestPostStatus
        from wiki_pipeline.db import SessionLocal

        session = SessionLocal()
        try:
            posts = (
                session.query(IngestPost)
                .filter(IngestPost.status == IngestPostStatus.pending)
                .order_by(IngestPost.created_at)
                .all()
            )
            ids = [p.id for p in posts]
            logger.info("Found %d pending posts: %s", len(ids), ids)
            return ids
        finally:
            session.close()

    @task
    def ocr_images(post_id: int) -> dict:
        """OCR a single post's images. Failures are isolated to this task."""
        from app.models.ingest import IngestPost, IngestPostStatus
        from dags._common import mark_post_failed
        from wiki_pipeline.db import SessionLocal
        from wiki_pipeline.ocr import process_post_images

        try:
            session = SessionLocal()
            try:
                post = session.get(IngestPost, post_id)
                if post:
                    post.status = IngestPostStatus.ocr_running
                    session.commit()
            finally:
                session.close()

            results = process_post_images(post_id)

            session = SessionLocal()
            try:
                post = session.get(IngestPost, post_id)
                if post:
                    post.status = IngestPostStatus.ocr_done
                    session.commit()
            finally:
                session.close()

            return {"post_id": post_id, "ocr_count": len(results), "success": True}
        except Exception as e:
            logger.error("OCR failed for post %s: %s", post_id, e, exc_info=True)
            mark_post_failed(post_id, str(e))
            return {"post_id": post_id, "ocr_count": 0, "success": False}

    @task(trigger_rule="all_done")
    def run_ingest(post_ids: list[int]) -> dict:
        """Ingest posts one at a time. Per-post failures don't abort the run.

        `all_done` trigger ensures we still attempt ingest even if a few OCR
        tasks failed.
        """
        from wiki_pipeline.ingest import ingest_post

        succeeded: list[int] = []
        failed: list[int] = []

        for post_id in post_ids:
            try:
                result = ingest_post(post_id)
                if result.success:
                    succeeded.append(post_id)
                    logger.info(
                        "Ingest succeeded for post %s: commit %s",
                        post_id,
                        result.commit_sha,
                    )
                else:
                    failed.append(post_id)
                    logger.error(
                        "Ingest failed for post %s: %s", post_id, result.error
                    )
            except Exception as e:
                failed.append(post_id)
                logger.error(
                    "Ingest exception for post %s: %s", post_id, e, exc_info=True
                )

        return {"succeeded": succeeded, "failed": failed}

    @task(trigger_rule="all_done")
    def update_index_and_commit(ingest_result: dict) -> dict:
        """Rebuild index.md from DB and make one summary commit per run."""
        succeeded = ingest_result.get("succeeded", []) if ingest_result else []
        if not succeeded:
            logger.info("No successful ingests — skipping index update")
            return {"committed": False}

        try:
            from app.models.wiki import WikiPage
            from wiki_pipeline.db import SessionLocal
            from wiki_pipeline.wiki_repo import (
                append_log,
                commit_changes,
                update_index_md,
            )

            session = SessionLocal()
            try:
                pages = session.query(WikiPage).all()
                pages_summary = [
                    {
                        "path": p.path,
                        "title": p.title,
                        "category": p.category,
                        "summary": p.summary,
                    }
                    for p in pages
                ]
            finally:
                session.close()

            update_index_md(pages_summary)
            append_log(
                "Daily ingest run\n"
                f"Succeeded: {succeeded}\n"
                f"Date: {datetime.now().isoformat()}"
            )
            sha = commit_changes(
                f"wiki_ingest_daily: {len(succeeded)} posts processed\n\n"
                f"Post IDs: {succeeded}"
            )
            logger.info("Index updated and committed: %s", sha)
            return {
                "committed": True,
                "sha": sha,
                "succeeded_count": len(succeeded),
            }
        except Exception as e:
            logger.error("Index update failed: %s", e, exc_info=True)
            return {"committed": False, "error": str(e)}

    @task(trigger_rule="all_done")
    def notify(index_result: dict, ingest_result: dict) -> None:
        """Log a one-line summary of the run."""
        succeeded = (ingest_result or {}).get("succeeded", [])
        failed = (ingest_result or {}).get("failed", [])
        committed = (index_result or {}).get("committed", False)
        logger.info(
            "wiki_ingest_daily complete — succeeded: %d, failed: %d, "
            "index_committed: %s",
            len(succeeded),
            len(failed),
            committed,
        )

    # --- DAG wiring ---
    post_ids = fetch_pending_posts()

    # Dynamic Task Mapping: one OCR task per post, run in parallel.
    ocr_results = ocr_images.expand(post_id=post_ids)

    # Sequential ingest (avoids commit/index race conditions).
    ingest_result = run_ingest(post_ids)
    ingest_result.set_upstream(ocr_results)

    index_result = update_index_and_commit(ingest_result)

    notify(index_result, ingest_result)
