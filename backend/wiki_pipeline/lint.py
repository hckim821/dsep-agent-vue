"""Lint pipeline — periodic wiki health checks (orphans, broken links, contradictions)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from wiki_pipeline.db import get_session


@dataclass
class LintFinding:
    type: str  # contradiction | orphan | stale | missing_entity | broken_link
    description: str
    severity: str = "medium"
    page_ids: list[int] = field(default_factory=list)


_SKIP_PATHS = {"index.md", "log.md", "schema.md"}


def run_lint(check_types: Optional[list[str]] = None) -> list[LintFinding]:
    """Run lint checks and persist findings to the DB.

    `check_types` is a subset of {"orphan", "broken_link", "missing_entity",
    "stale", "contradiction"}. None means run all of them except the
    expensive LLM-based contradiction check (opt-in only).
    """
    from app.models.lint import (
        LintFinding as DBLintFinding,
        LintFindingSeverity,
        LintFindingType,
    )
    from app.models.wiki import WikiPage

    selected = check_types or ["orphan", "broken_link", "missing_entity", "stale"]
    findings: list[LintFinding] = []

    with get_session() as session:
        pages = session.query(WikiPage).all()

        if pages:
            if "orphan" in selected:
                findings.extend(_detect_orphans(session, pages))
            if "broken_link" in selected:
                findings.extend(_detect_broken_links(session, pages))
            if "missing_entity" in selected:
                findings.extend(_detect_missing_entities(session, pages))
            if "stale" in selected:
                findings.extend(_detect_stale(session, pages))
            if "contradiction" in selected:
                findings.extend(_detect_contradictions_llm(session, pages))

        # 동일 type+description 중복 방지 (이전 점검과 비교)
        existing = session.query(DBLintFinding).filter(
            DBLintFinding.resolved_at.is_(None)
        ).all()
        existing_keys = {(f.type.value if hasattr(f.type, "value") else f.type, f.description) for f in existing}

        added = 0
        for f in findings:
            key = (f.type, f.description)
            if key in existing_keys:
                continue
            session.add(
                DBLintFinding(
                    type=LintFindingType(f.type),
                    page_ids_json=f.page_ids,
                    description=f.description,
                    severity=LintFindingSeverity(f.severity),
                    detected_at=datetime.now(timezone.utc),
                )
            )
            existing_keys.add(key)
            added += 1

    return findings


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _detect_orphans(session, pages) -> list[LintFinding]:
    """Pages with zero incoming wiki links."""
    from app.models.wiki import WikiBacklink

    findings: list[LintFinding] = []
    for page in pages:
        if page.path in _SKIP_PATHS:
            continue
        count = (
            session.query(WikiBacklink)
            .filter(WikiBacklink.to_page_id == page.id)
            .count()
        )
        if count == 0:
            findings.append(
                LintFinding(
                    type="orphan",
                    description=f"Page '{page.path}' has no incoming links",
                    severity="low",
                    page_ids=[page.id],
                )
            )
    return findings


def _detect_broken_links(session, pages) -> list[LintFinding]:
    """[[Links]] that don't resolve to any existing page title."""
    from wiki_pipeline.wiki_repo import extract_backlinks, read_page

    findings: list[LintFinding] = []
    page_titles = {p.title for p in pages}

    for page in pages:
        content = read_page(page.path)
        if not content:
            continue
        seen: set[str] = set()
        for link_title in extract_backlinks(content):
            if link_title in seen:
                continue
            seen.add(link_title)
            if link_title not in page_titles:
                findings.append(
                    LintFinding(
                        type="broken_link",
                        description=(
                            f"Page '{page.path}' links to non-existent '[[{link_title}]]'"
                        ),
                        severity="medium",
                        page_ids=[page.id],
                    )
                )
    return findings


def _detect_missing_entities(session, pages) -> list[LintFinding]:
    """Titles referenced by [[...]] but not yet captured as wiki pages."""
    from wiki_pipeline.wiki_repo import extract_backlinks, read_page

    findings: list[LintFinding] = []
    page_titles = {p.title for p in pages}

    mentioned: set[str] = set()
    for page in pages:
        content = read_page(page.path)
        if content:
            for link in extract_backlinks(content):
                mentioned.add(link)

    for title in sorted(mentioned - page_titles):
        findings.append(
            LintFinding(
                type="missing_entity",
                description=f"'{title}' is referenced but has no wiki page",
                severity="medium",
                page_ids=[],
            )
        )
    return findings


def _detect_stale(session, pages, days: int = 90) -> list[LintFinding]:
    """Pages whose updated_at is older than N days."""
    findings: list[LintFinding] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    for page in pages:
        if page.path in _SKIP_PATHS:
            continue
        updated = page.updated_at
        if not updated:
            continue
        # Normalize to UTC for comparison
        if updated.tzinfo is None:
            updated_aware = updated.replace(tzinfo=timezone.utc)
        else:
            updated_aware = updated.astimezone(timezone.utc)
        if updated_aware < cutoff:
            findings.append(
                LintFinding(
                    type="stale",
                    description=(
                        f"Page '{page.path}' not updated in {days}+ days "
                        f"(last: {updated_aware.date()})"
                    ),
                    severity="low",
                    page_ids=[page.id],
                )
            )
    return findings


def _detect_contradictions_llm(session, pages) -> list[LintFinding]:
    """LLM-assisted contradiction detection — expensive, runs per-category."""
    from wiki_pipeline.llm_client import get_llm_client
    from wiki_pipeline.wiki_repo import read_page

    findings: list[LintFinding] = []
    if len(pages) < 2:
        return findings

    by_cat: dict[str, list] = {}
    for p in pages:
        if p.path in _SKIP_PATHS:
            continue
        cat = p.category or "misc"
        by_cat.setdefault(cat, []).append(p)

    llm = get_llm_client()
    prompt = _load_prompt("lint_contradiction.md")

    for cat, cat_pages in by_cat.items():
        if len(cat_pages) < 2:
            continue
        sample = cat_pages[:3]  # cap token cost
        combined = "\n\n---\n\n".join(
            f"## {p.path}\n{read_page(p.path) or '(empty)'}" for p in sample
        )
        try:
            resp = llm.complete(
                [
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": f"Review these wiki pages for contradictions:\n\n{combined}",
                    },
                ],
                task="lint",
            )
        except Exception:
            continue

        text = resp.content or ""
        if "contradiction" in text.lower() or "모순" in text:
            findings.append(
                LintFinding(
                    type="contradiction",
                    description=text[:500],
                    severity="high",
                    page_ids=[p.id for p in sample],
                )
            )
    return findings


def _load_prompt(filename: str) -> str:
    prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
    path = os.path.join(prompts_dir, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return "You are a wiki quality checker."
