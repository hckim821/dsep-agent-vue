"""Ingest pipeline — turns an `ingest_posts` row into wiki page edits + a git commit.

Implements the 9-step flow from design spec section 9.2:
    1. Load post + OCR results + metadata from DB
    2. Show LLM the current wiki index (list_pages)
    3. LLM identifies affected pages (create / update / cross-ref)
    4. Read current content of each target page
    5. LLM generates new markdown for each page
    6. Add source attribution section to each page
    7. Update wiki_pages, wiki_page_sources, wiki_backlinks in DB
    8. Update index.md, log.md
    9. Git commit
"""
from __future__ import annotations

import json
import os
import re
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from wiki_pipeline.db import get_session
from wiki_pipeline.llm_client import get_llm_client
from wiki_pipeline.ocr import process_post_images
from wiki_pipeline.wiki_repo import (
    append_log,
    commit_changes,
    extract_backlinks,
    list_pages,
    read_page,
    update_index_md,
    write_page,
)


@dataclass
class IngestResult:
    post_id: int
    success: bool
    created_pages: list[int] = field(default_factory=list)
    updated_pages: list[int] = field(default_factory=list)
    commit_sha: Optional[str] = None
    tokens_used: int = 0
    error: Optional[str] = None


def ingest_post(post_id: int) -> IngestResult:
    """Run the full ingest flow for one post. See module docstring."""
    from app.models.ingest import (
        IngestAttachment,
        IngestJob,
        IngestJobStage,
        IngestJobStatus,
        IngestPost,
        IngestPostStatus,
    )
    from app.models.wiki import WikiPage, WikiPageSource, WikiPageSourceRelation

    result = IngestResult(post_id=post_id, success=False)

    with get_session() as session:
        post = session.get(IngestPost, post_id)
        if not post:
            result.error = f"Post {post_id} not found"
            return result

        # OCR 단계 (vision 모델이 설정된 경우만)
        post.status = IngestPostStatus.ocr_running
        session.flush()
        try:
            process_post_images(post_id)
        except Exception:
            # OCR 실패해도 ingest는 계속 진행
            pass
        post.status = IngestPostStatus.ingest_running
        session.flush()

        job = IngestJob(
            post_id=post_id,
            stage=IngestJobStage.ingest,
            status=IngestJobStatus.running,
            started_at=datetime.now(timezone.utc),
        )
        session.add(job)
        session.flush()

        try:
            llm = get_llm_client()

            # --- Step 1: build context from post + attachment OCR ---
            attachments = (
                session.query(IngestAttachment)
                .filter(IngestAttachment.post_id == post_id)
                .all()
            )
            ocr_blocks: list[str] = []
            for att in attachments:
                if att.ocr_text:
                    ocr_blocks.append(
                        f"[Attachment: {att.original_filename}]\n{att.ocr_text}"
                    )

            context_parts: list[str] = [
                f"# Ingest Post #{post_id}: {post.title}",
                f"**Type**: {post.type.value}",
                f"**Category hint**: {post.category or 'none'}",
            ]
            if post.source_url:
                context_parts.append(f"**Source URL**: {post.source_url}")
            if post.source_author:
                context_parts.append(f"**Source Author**: {post.source_author}")
            context_parts.append(f"\n## Content\n{post.body_md}")
            if ocr_blocks:
                context_parts.append("\n## Attached Image Text\n" + "\n\n".join(ocr_blocks))
            context_text = "\n".join(context_parts)

            # --- Step 2: current wiki state ---
            all_paths = list_pages()
            pages_listing = "\n".join(f"- {p}" for p in all_paths) or "(empty wiki)"

            # --- Step 3: ask LLM for a create/update plan ---
            base_prompt = (
                _load_prompt("correction_system.md")
                if post.type.value == "correction"
                else _load_prompt("ingest_system.md")
            )
            schema_prompt = _load_active_schema(session)
            system_prompt = base_prompt
            if schema_prompt:
                system_prompt = (
                    f"{base_prompt}\n\n"
                    "## Wiki Schema (current active version)\n"
                    f"{schema_prompt}\n\n"
                    "Follow the schema above strictly when creating or editing pages."
                )

            # type=correction: 강제로 target_wiki_path를 update에 포함
            correction_hint = ""
            if post.type.value == "correction" and post.target_wiki_path:
                correction_hint = (
                    f"\n\nIMPORTANT: This is a CORRECTION proposal targeting `{post.target_wiki_path}`. "
                    "You MUST include this path in the 'update' list. "
                    "Carefully reconcile the proposal with existing content; "
                    "if the proposal contradicts existing facts, document both views with sources."
                )

            plan_messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Current wiki pages:\n{pages_listing}\n\n"
                        f"New ingest content:\n{context_text}{correction_hint}\n\n"
                        "Respond with a JSON plan in this exact shape:\n"
                        '{"create": ["path/to/new.md"], "update": ["path/to/existing.md"], "cross_ref": ["path/to/ref.md"]}\n'
                        "Only include paths under known top-level categories "
                        "(concepts/, entities/, comparisons/, etc.). "
                        "Omit a key if empty."
                    ),
                },
            ]

            plan_response = llm.complete(plan_messages, task="ingest")
            result.tokens_used += plan_response.tokens_used
            plan = _parse_page_plan(plan_response.content)

            # --- Step 4-5: generate content per page ---
            create_paths = plan.get("create", []) or []
            update_paths = plan.get("update", []) or []
            cross_ref_paths = plan.get("cross_ref", []) or []
            affected_paths: list[str] = []
            for p in create_paths + update_paths + cross_ref_paths:
                if p and p not in affected_paths:
                    affected_paths.append(p)

            page_contents: dict[str, str] = {}
            for page_path in affected_paths:
                current_content = read_page(page_path)
                if page_path in create_paths:
                    action = "create"
                elif page_path in update_paths:
                    action = "update"
                else:
                    action = "cross_ref_update"

                gen_messages = [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Ingest content:\n{context_text}\n\n"
                            f"Action: {action} page `{page_path}`\n"
                            + (f"Current content:\n{current_content}\n\n" if current_content else "")
                            + "Generate the COMPLETE new markdown content for this page. "
                            "Start with an H1 title. Use [[PageTitle]] syntax for cross-references."
                        ),
                    },
                ]
                gen_response = llm.complete(gen_messages, task="ingest")
                result.tokens_used += gen_response.tokens_used

                # --- Step 6: source attribution ---
                page_contents[page_path] = _add_source_attribution(
                    gen_response.content, post_id, post.title
                )

            # Write files to wiki repo
            for path, content in page_contents.items():
                write_page(path, content)

            # --- Step 7: DB updates ---
            created_ids: list[int] = []
            updated_ids: list[int] = []
            for page_path, content in page_contents.items():
                title = _extract_title(content) or page_path
                category = page_path.split("/")[0] if "/" in page_path else None

                existing = (
                    session.query(WikiPage).filter(WikiPage.path == page_path).first()
                )
                if existing:
                    existing.title = title
                    existing.category = category
                    existing.last_ingest_id = post_id
                    wiki_page = existing
                    updated_ids.append(existing.id)
                    relation = WikiPageSourceRelation.updated
                else:
                    wiki_page = WikiPage(
                        path=page_path,
                        title=title,
                        category=category,
                        last_ingest_id=post_id,
                    )
                    session.add(wiki_page)
                    session.flush()
                    created_ids.append(wiki_page.id)
                    relation = WikiPageSourceRelation.created

                session.add(
                    WikiPageSource(
                        wiki_page_id=wiki_page.id,
                        ingest_post_id=post_id,
                        relation=relation,
                    )
                )
                _update_backlinks(session, wiki_page.id, content)

            result.created_pages = created_ids
            result.updated_pages = updated_ids
            session.flush()

            # --- Step 8: index.md + log.md ---
            all_wiki_pages = session.query(WikiPage).all()
            pages_summary = [
                {
                    "path": p.path,
                    "title": p.title,
                    "category": p.category,
                    "summary": p.summary,
                }
                for p in all_wiki_pages
            ]
            update_index_md(pages_summary)
            append_log(
                f"Ingest #{post_id}: {post.title}\n"
                f"- Created: {len(created_ids)} page(s) — {created_ids}\n"
                f"- Updated: {len(updated_ids)} page(s) — {updated_ids}\n"
                f"- Tokens: {result.tokens_used}"
            )

            # --- Step 9: git commit ---
            ingest_model = os.getenv("VLLM_INGEST_MODEL", "unknown")
            commit_msg = (
                f"ingest/{post_id}: {post.title}\n\n"
                f"Created: {', '.join(create_paths) or '(none)'}\n"
                f"Updated: {', '.join(update_paths) or '(none)'}\n"
                f"Cross-ref: {', '.join(cross_ref_paths) or '(none)'}\n"
                f"Tokens: {result.tokens_used} | Model: {ingest_model}"
            )
            commit_sha = commit_changes(commit_msg)
            result.commit_sha = commit_sha

            if page_contents:
                touched_pages = (
                    session.query(WikiPage)
                    .filter(WikiPage.path.in_(list(page_contents.keys())))
                    .all()
                )
                for wp in touched_pages:
                    wp.current_commit_sha = commit_sha

            post.status = IngestPostStatus.done
            job.status = IngestJobStatus.success
            job.finished_at = datetime.now(timezone.utc)
            job.tokens_used = result.tokens_used
            job.model_used = ingest_model
            job.log_text = (
                f"Created: {created_ids}\nUpdated: {updated_ids}\nCommit: {commit_sha}"
            )

            result.success = True

        except Exception as e:
            post.status = IngestPostStatus.failed
            job.status = IngestJobStatus.failed
            job.finished_at = datetime.now(timezone.utc)
            job.error_text = traceback.format_exc()
            job.tokens_used = result.tokens_used
            result.error = str(e)
            # The context manager will commit the failure record (status=failed),
            # then re-raise. We swallow re-raise so callers get a structured result.

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_prompt(filename: str) -> str:
    prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
    path = os.path.join(prompts_dir, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return "You are a wiki management assistant."


def _load_active_schema(session) -> str:
    """Load the latest schema_versions row content. Returns empty string on miss."""
    try:
        from app.models.schema_version import SchemaVersion
        latest = (
            session.query(SchemaVersion)
            .order_by(SchemaVersion.updated_at.desc())
            .first()
        )
        return (latest.content or "") if latest else ""
    except Exception:
        return ""


def _parse_page_plan(llm_response: str) -> dict:
    """Extract a {"create": [...], "update": [...], "cross_ref": [...]} dict from LLM text.

    Tolerant of surrounding prose and ```json fences.
    """
    if not llm_response:
        return {"create": [], "update": [], "cross_ref": []}

    # Strip markdown code fences first
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", llm_response, re.DOTALL)
    candidates: list[str] = []
    if fenced:
        candidates.append(fenced.group(1))

    # Greedy/balanced-ish scan: every {...} block, ranked by presence of expected keys
    for match in re.finditer(r"\{[^{}]*\}", llm_response, re.DOTALL):
        candidates.append(match.group(0))

    for blob in candidates:
        try:
            parsed = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        if any(k in parsed for k in ("create", "update", "cross_ref")):
            return {
                "create": list(parsed.get("create") or []),
                "update": list(parsed.get("update") or []),
                "cross_ref": list(parsed.get("cross_ref") or []),
            }

    return {"create": [], "update": [], "cross_ref": []}


def _add_source_attribution(content: str, post_id: int, post_title: str) -> str:
    """Append (or extend) a `## 출처` section pointing to the ingest post."""
    entry = f"- Ingest #{post_id}: {post_title}"
    if "## 출처" in content:
        if entry in content:
            return content
        return content.rstrip() + f"\n{entry}\n"
    return content.rstrip() + f"\n\n## 출처\n{entry}\n"


def _extract_title(content: str) -> Optional[str]:
    """Extract the first H1 heading from a markdown body."""
    m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    return m.group(1).strip() if m else None


def _update_backlinks(session, from_page_id: int, content: str) -> None:
    """Replace this page's outgoing backlinks based on `[[Title]]` mentions."""
    from app.models.wiki import WikiBacklink, WikiPage

    link_titles = extract_backlinks(content)

    session.query(WikiBacklink).filter(
        WikiBacklink.from_page_id == from_page_id
    ).delete(synchronize_session=False)

    seen_targets: set[int] = set()
    for title in link_titles:
        target = session.query(WikiPage).filter(WikiPage.title == title).first()
        if not target or target.id == from_page_id or target.id in seen_targets:
            continue
        seen_targets.add(target.id)
        session.add(WikiBacklink(from_page_id=from_page_id, to_page_id=target.id))
