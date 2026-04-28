"""OCR module — Phase 2: vision LLM via OpenAI-compatible endpoint (Ollama / vLLM).

Reads images from `ingest_attachments`, asks a vision-capable model to extract
the text/describe the diagram, and stores the result back into
`ingest_attachments.ocr_text`. Falls back to a stub if no vision model is
configured.
"""
from __future__ import annotations

import base64
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# 백엔드 경로 등록
_THIS_DIR = os.path.dirname(__file__)
_BACKEND_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


@dataclass
class OCRResult:
    attachment_id: int
    post_id: int
    text: str
    model: str


def _vision_model() -> Optional[str]:
    """Return configured vision model name, or None if disabled."""
    model = os.getenv("VLLM_VISION_MODEL", "").strip()
    return model or None


def _ocr_one_image(image_path: Path, model: str) -> str:
    """Run vision LLM on a single image. Returns extracted text/description."""
    from openai import OpenAI

    base_url = os.getenv("VLLM_BASE_URL", "http://localhost:11434/v1")
    api_key = os.getenv("VLLM_API_KEY", "ollama")
    client = OpenAI(base_url=base_url, api_key=api_key)

    data = image_path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    ext = image_path.suffix.lstrip(".").lower()
    mime = f"image/{'jpeg' if ext == 'jpg' else ext}"

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract textual content from images for a knowledge wiki. "
                    "If the image is a diagram or chart, describe its structure and labels. "
                    "If it's a screenshot, transcribe the text verbatim. "
                    "Reply in the same language as the image."
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all text and describe the visual content."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            },
        ],
        temperature=0.1,
        max_tokens=1024,
    )
    return resp.choices[0].message.content or ""


def process_post_images(post_id: int) -> list[OCRResult]:
    """OCR all image attachments for one post.

    - Skips attachments that already have ocr_text.
    - Skips non-image attachments.
    - Returns empty list if VLLM_VISION_MODEL is not set.
    """
    model = _vision_model()
    if not model:
        return []

    from app.models.ingest import IngestAttachment
    from wiki_pipeline.db import get_session
    from wiki_pipeline.storage import get_file_path

    results: list[OCRResult] = []

    with get_session() as session:
        attachments = (
            session.query(IngestAttachment)
            .filter(IngestAttachment.post_id == post_id)
            .all()
        )
        for att in attachments:
            if att.ocr_text:
                continue
            ext = Path(att.original_filename).suffix.lower()
            if ext not in IMAGE_EXTS:
                continue
            try:
                full_path = get_file_path(att.file_path)
                if not full_path.exists():
                    continue
                text = _ocr_one_image(full_path, model)
                if text:
                    att.ocr_text = text
                    att.ocr_model = model
                    att.ocr_done_at = datetime.now(timezone.utc)
                    results.append(OCRResult(
                        attachment_id=att.id,
                        post_id=post_id,
                        text=text,
                        model=model,
                    ))
            except Exception:
                # 한 이미지 실패가 나머지를 막지 않도록
                continue

    return results
