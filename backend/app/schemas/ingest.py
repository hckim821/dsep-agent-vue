from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class IngestPostCreate(BaseModel):
    title: str
    body_md: str
    type: str = "new"
    priority: str = "normal"
    category: Optional[str] = None
    source_url: Optional[str] = None
    source_author: Optional[str] = None
    source_date: Optional[date] = None
    target_wiki_path: Optional[str] = None
    target_section_anchor: Optional[str] = None


class IngestPostOut(BaseModel):
    id: int
    title: str
    body_md: str
    type: str
    priority: str
    category: Optional[str] = None
    status: str
    source_url: Optional[str] = None
    source_author: Optional[str] = None
    source_date: Optional[date] = None
    target_wiki_path: Optional[str] = None
    target_section_anchor: Optional[str] = None
    unverified: bool
    created_at: datetime
    updated_at: datetime
    author_id: int

    model_config = {"from_attributes": True}


class IngestJobOut(BaseModel):
    id: int
    stage: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    log_text: Optional[str] = None
    error_text: Optional[str] = None

    model_config = {"from_attributes": True}


class AttachmentOut(BaseModel):
    id: int
    original_filename: str
    stored_filename: str
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    ocr_done_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
