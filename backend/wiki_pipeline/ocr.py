"""OCR module — Phase 1 stub.

Real OCR (PaddleOCR / vision LLM) lands in Phase 3. This module is
imported by the ingest pipeline today so the call site is ready.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OCRResult:
    attachment_id: int
    post_id: int
    text: str
    model: str


def process_post_images(post_id: int) -> list[OCRResult]:
    """OCR all images attached to a post.

    Phase 1: no-op. Returns an empty list. The ingest pipeline simply
    consumes whatever `ingest_attachments.ocr_text` already holds.
    """
    return []
