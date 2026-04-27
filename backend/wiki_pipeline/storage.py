"""Local filesystem storage for ingest attachments. Path-traversal safe."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import TypedDict

ALLOWED_EXTENSIONS: set[str] = {"png", "jpg", "jpeg", "gif", "webp", "pdf", "txt", "md"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


class SavedFile(TypedDict):
    stored_filename: str
    file_path: str
    size_bytes: int


def get_storage_base() -> Path:
    """Resolved absolute root for all pipeline-managed files."""
    base = Path(os.getenv("STORAGE_BASE_PATH", "./storage")).resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def safe_post_dir(post_id: int, subdir: str = "original") -> Path:
    """Resolve and create the per-post directory, guaranteed under storage base."""
    base = get_storage_base()
    target = (base / "ingest" / str(int(post_id)) / subdir).resolve()
    if not _is_within(target, base):
        raise ValueError(f"Path traversal detected: {target}")
    target.mkdir(parents=True, exist_ok=True)
    return target


def save_upload(post_id: int, original_filename: str, data: bytes) -> SavedFile:
    """Save uploaded bytes for a post.

    Validates the extension against ALLOWED_EXTENSIONS and enforces
    MAX_FILE_SIZE. Returns a dict with the stored filename, the
    storage-base-relative path, and size in bytes.
    """
    ext = Path(original_filename).suffix.lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extension not allowed: {ext!r}")
    if len(data) > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {len(data)} bytes (max {MAX_FILE_SIZE})")

    stored_name = f"{uuid.uuid4().hex}.{ext}"
    dest_dir = safe_post_dir(post_id, "original")
    dest_path = dest_dir / stored_name
    dest_path.write_bytes(data)

    rel_path = str(dest_path.relative_to(get_storage_base())).replace("\\", "/")
    return {
        "stored_filename": stored_name,
        "file_path": rel_path,
        "size_bytes": len(data),
    }


def get_file_path(file_path: str) -> Path:
    """Resolve a storage-relative path to an absolute one, guarded against traversal."""
    base = get_storage_base()
    target = (base / file_path).resolve()
    if not _is_within(target, base):
        raise ValueError("Path traversal detected")
    return target
