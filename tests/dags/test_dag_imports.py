"""DAG import-validation tests.

These verify the DAG modules parse and register a `dag` object — they don't
exercise the scheduler. Skipped automatically when Airflow isn't installed.
"""
from __future__ import annotations

import importlib.util
import os
import sys

import pytest

airflow = pytest.importorskip("airflow")

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
)
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
DAGS_DIR = os.path.join(REPO_ROOT, "dags")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _load(module_name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        module_name, os.path.join(DAGS_DIR, filename)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_common_importable():
    mod = _load("_common", "_common.py")
    assert hasattr(mod, "mark_post_failed")
    assert hasattr(mod, "isolated_task")
    assert hasattr(mod, "BACKEND_DIR")


def test_ingest_dag_importable():
    mod = _load("wiki_ingest_daily", "wiki_ingest_daily.py")
    assert hasattr(mod, "dag")
    assert mod.dag.dag_id == "wiki_ingest_daily"
    # `schedule` (Airflow 2.4+) supersedes `schedule_interval`; both stay readable.
    assert getattr(mod.dag, "schedule_interval", None) == "0 2 * * *"


def test_lint_dag_importable():
    mod = _load("wiki_lint_weekly", "wiki_lint_weekly.py")
    assert hasattr(mod, "dag")
    assert mod.dag.dag_id == "wiki_lint_weekly"
    assert getattr(mod.dag, "schedule_interval", None) == "0 3 * * 0"


def test_ingest_dag_task_ids():
    mod = _load("wiki_ingest_daily", "wiki_ingest_daily.py")
    task_ids = {t.task_id for t in mod.dag.tasks}
    expected = {
        "fetch_pending_posts",
        "ocr_images",
        "run_ingest",
        "update_index_and_commit",
        "notify",
    }
    assert expected.issubset(task_ids), f"missing: {expected - task_ids}"


def test_lint_dag_task_ids():
    mod = _load("wiki_lint_weekly", "wiki_lint_weekly.py")
    task_ids = {t.task_id for t in mod.dag.tasks}
    expected = {
        "load_wiki_snapshot",
        "detect_orphans",
        "detect_stale",
        "detect_missing_entities",
        "detect_broken_links",
        "aggregate_findings",
    }
    assert expected.issubset(task_ids), f"missing: {expected - task_ids}"
