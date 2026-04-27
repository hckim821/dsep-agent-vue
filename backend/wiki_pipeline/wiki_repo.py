"""Git-backed wiki repository: markdown read/write, backlinks, commits."""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import git

_BACKLINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def get_wiki_repo_path() -> Path:
    return Path(os.getenv("WIKI_REPO_PATH", "./wiki_repo")).resolve()


def get_repo() -> git.Repo:
    """Return the GitPython Repo object for the wiki working copy."""
    return git.Repo(get_wiki_repo_path())


def _full_path(path: str) -> Path:
    base = get_wiki_repo_path()
    full = (base / path).resolve()
    if base not in full.parents and full != base:
        raise ValueError(f"Path escapes wiki repo: {path}")
    return full


def read_page(path: str) -> Optional[str]:
    """Read markdown content of a wiki page. Returns None if missing."""
    full = _full_path(path)
    if not full.exists():
        return None
    return full.read_text(encoding="utf-8")


def write_page(path: str, content: str) -> None:
    """Write markdown content; create parent dirs as needed."""
    full = _full_path(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")


def list_pages() -> list[str]:
    """All .md files in the wiki repo, relative paths with forward slashes."""
    base = get_wiki_repo_path()
    pages: list[str] = []
    for p in base.rglob("*.md"):
        if ".git" in p.parts:
            continue
        pages.append(str(p.relative_to(base)).replace("\\", "/"))
    return sorted(pages)


def extract_backlinks(content: str) -> list[str]:
    """Extract `[[Page Title]]` style wiki links from a markdown body."""
    if not content:
        return []
    return [m.strip() for m in _BACKLINK_RE.findall(content) if m.strip()]


def commit_changes(
    message: str,
    author_name: str = "LLM Wiki Bot",
    author_email: str = "bot@llmwiki.local",
) -> str:
    """Stage all changes and commit. Returns commit SHA (or HEAD SHA if nothing changed)."""
    repo = get_repo()
    repo.git.add("--all")
    # repo.is_dirty(index=True) checks if staged tree differs from HEAD
    if not repo.is_dirty(index=True, working_tree=False, untracked_files=False):
        try:
            return repo.head.commit.hexsha
        except Exception:
            # Empty repo (no HEAD yet) — fall through to create initial commit
            pass
    actor = git.Actor(author_name, author_email)
    commit = repo.index.commit(message, author=actor, committer=actor)
    return commit.hexsha


def update_index_md(pages_summary: list[dict]) -> None:
    """Rebuild index.md grouped by category from a wiki_pages summary list.

    `pages_summary` items: {"path", "title", "category", "summary"}.
    """
    by_category: dict[str, list[dict]] = {}
    for p in pages_summary:
        if p.get("path") in ("index.md", "log.md"):
            continue
        cat = p.get("category") or "misc"
        by_category.setdefault(cat, []).append(p)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# LLM Wiki Index",
        "",
        f"마지막 업데이트: {timestamp}",
    ]
    for cat in sorted(by_category):
        lines.append("")
        lines.append(f"## {cat}/")
        lines.append("")
        for item in sorted(by_category[cat], key=lambda x: (x.get("title") or "")):
            title = item.get("title") or item.get("path") or "(untitled)"
            path = item.get("path") or ""
            summary = (item.get("summary") or "").strip().replace("\n", " ")
            suffix = f" — {summary}" if summary else ""
            lines.append(f"- [[{title}]]({path}){suffix}")

    write_page("index.md", "\n".join(lines) + "\n")


def append_log(entry: str) -> None:
    """Append a timestamped entry to log.md."""
    log_path = _full_path("log.md")
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else "# LLM Wiki Change Log\n"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path.write_text(
        existing.rstrip() + f"\n\n## {timestamp}\n{entry}\n",
        encoding="utf-8",
    )
