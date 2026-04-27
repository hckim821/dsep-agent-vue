"""Weekly wiki lint DAG: detect orphans / stale / missing entities / broken links.

Flow (design spec 8.2):
    load_wiki_snapshot
        -> detect_orphans, detect_stale, detect_missing_entities,
           detect_broken_links   (4 checks, parallel)
        -> aggregate_findings    (write to lint_findings table)
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import timedelta

import pendulum
from airflow import DAG
from airflow.decorators import task

BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "backend")
)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

logger = logging.getLogger("llmwiki.lint_weekly")

default_args = {
    "owner": "llmwiki",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


with DAG(
    dag_id="wiki_lint_weekly",
    default_args=default_args,
    description="Weekly wiki lint: orphans, stale, missing entities, broken links",
    schedule="0 3 * * 0",
    start_date=pendulum.today("UTC").subtract(days=1),
    catchup=False,
    tags=["llmwiki", "lint"],
    max_active_runs=1,
) as dag:

    @task
    def load_wiki_snapshot() -> dict:
        """Coarse counters for the run; the per-check tasks re-query for fresh state."""
        from app.models.wiki import WikiPage
        from wiki_pipeline.db import SessionLocal

        session = SessionLocal()
        try:
            pages = session.query(WikiPage).all()
            snapshot = {
                "total_pages": len(pages),
                "page_ids": [p.id for p in pages],
                "categories": sorted({p.category for p in pages if p.category}),
            }
            logger.info("Wiki snapshot: %d pages", snapshot["total_pages"])
            return snapshot
        finally:
            session.close()

    def _finding_to_dict(f) -> dict:
        return {
            "type": f.type,
            "description": f.description,
            "severity": f.severity,
            "page_ids": list(f.page_ids or []),
        }

    @task
    def detect_orphans(snapshot: dict) -> list[dict]:
        """Pages with zero incoming wiki links."""
        try:
            from app.models.wiki import WikiPage
            from wiki_pipeline.db import SessionLocal
            from wiki_pipeline.lint import _detect_orphans

            session = SessionLocal()
            try:
                pages = session.query(WikiPage).all()
                findings = _detect_orphans(session, pages)
            finally:
                session.close()
            return [_finding_to_dict(f) for f in findings]
        except Exception as e:
            logger.error("detect_orphans failed: %s", e, exc_info=True)
            return []

    @task
    def detect_stale(snapshot: dict) -> list[dict]:
        """Pages whose `updated_at` is older than 90 days."""
        try:
            from app.models.wiki import WikiPage
            from wiki_pipeline.db import SessionLocal
            from wiki_pipeline.lint import _detect_stale

            session = SessionLocal()
            try:
                pages = session.query(WikiPage).all()
                findings = _detect_stale(session, pages)
            finally:
                session.close()
            return [_finding_to_dict(f) for f in findings]
        except Exception as e:
            logger.error("detect_stale failed: %s", e, exc_info=True)
            return []

    @task
    def detect_missing_entities(snapshot: dict) -> list[dict]:
        """Titles referenced via `[[...]]` but not yet captured as pages."""
        try:
            from app.models.wiki import WikiPage
            from wiki_pipeline.db import SessionLocal
            from wiki_pipeline.lint import _detect_missing_entities

            session = SessionLocal()
            try:
                pages = session.query(WikiPage).all()
                findings = _detect_missing_entities(session, pages)
            finally:
                session.close()
            return [_finding_to_dict(f) for f in findings]
        except Exception as e:
            logger.error("detect_missing_entities failed: %s", e, exc_info=True)
            return []

    @task
    def detect_broken_links(snapshot: dict) -> list[dict]:
        """`[[Title]]` links whose target page doesn't exist."""
        try:
            from app.models.wiki import WikiPage
            from wiki_pipeline.db import SessionLocal
            from wiki_pipeline.lint import _detect_broken_links

            session = SessionLocal()
            try:
                pages = session.query(WikiPage).all()
                findings = _detect_broken_links(session, pages)
            finally:
                session.close()
            return [_finding_to_dict(f) for f in findings]
        except Exception as e:
            logger.error("detect_broken_links failed: %s", e, exc_info=True)
            return []

    @task(trigger_rule="all_done")
    def aggregate_findings(
        orphans: list[dict],
        stale: list[dict],
        missing: list[dict],
        broken: list[dict],
    ) -> dict:
        """Persist the union of all findings to the `lint_findings` table."""
        from datetime import datetime, timezone

        from app.models.lint import (
            LintFinding,
            LintFindingSeverity,
            LintFindingType,
        )
        from wiki_pipeline.db import SessionLocal

        all_findings = (
            (orphans or []) + (stale or []) + (missing or []) + (broken or [])
        )

        session = SessionLocal()
        try:
            saved = 0
            for f in all_findings:
                session.add(
                    LintFinding(
                        type=LintFindingType(f["type"]),
                        page_ids_json=list(f.get("page_ids") or []),
                        description=f.get("description"),
                        severity=LintFindingSeverity(f.get("severity", "medium")),
                        detected_at=datetime.now(timezone.utc),
                    )
                )
                saved += 1
            session.commit()
            logger.info("Saved %d lint findings", saved)
            return {
                "saved": saved,
                "breakdown": {
                    "orphans": len(orphans or []),
                    "stale": len(stale or []),
                    "missing_entities": len(missing or []),
                    "broken_links": len(broken or []),
                },
            }
        except Exception as e:
            session.rollback()
            logger.error("aggregate_findings failed: %s", e, exc_info=True)
            return {"saved": 0, "error": str(e)}
        finally:
            session.close()

    # --- DAG wiring ---
    snapshot = load_wiki_snapshot()

    orphan_findings = detect_orphans(snapshot)
    stale_findings = detect_stale(snapshot)
    missing_findings = detect_missing_entities(snapshot)
    broken_findings = detect_broken_links(snapshot)

    aggregate_findings(
        orphan_findings, stale_findings, missing_findings, broken_findings
    )
