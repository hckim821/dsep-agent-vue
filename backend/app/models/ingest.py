import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    TIMESTAMP,
    Text,
    func,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IngestPostType(str, enum.Enum):
    new = "new"
    correction = "correction"
    chat_summary = "chat_summary"


class IngestPostPriority(str, enum.Enum):
    normal = "normal"
    urgent = "urgent"


class IngestPostStatus(str, enum.Enum):
    pending = "pending"
    ocr_running = "ocr_running"
    ocr_done = "ocr_done"
    ingest_running = "ingest_running"
    ingest_done = "ingest_done"
    done = "done"
    failed = "failed"


class IngestJobStage(str, enum.Enum):
    ocr = "ocr"
    ingest = "ingest"
    lint = "lint"


class IngestJobStatus(str, enum.Enum):
    running = "running"
    success = "success"
    failed = "failed"


class IngestPost(Base):
    __tablename__ = "ingest_posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", name="fk_ingest_posts_author"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body_md: Mapped[str] = mapped_column(MEDIUMTEXT, nullable=False)
    type: Mapped[IngestPostType] = mapped_column(
        Enum(IngestPostType, name="ingest_post_type"),
        nullable=False,
        default=IngestPostType.new,
    )
    priority: Mapped[IngestPostPriority] = mapped_column(
        Enum(IngestPostPriority, name="ingest_post_priority"),
        nullable=False,
        default=IngestPostPriority.normal,
    )
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[IngestPostStatus] = mapped_column(
        Enum(IngestPostStatus, name="ingest_post_status"),
        nullable=False,
        default=IngestPostStatus.pending,
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    target_wiki_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    target_section_anchor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    unverified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_ingest_posts_status", "status"),
        Index("idx_ingest_posts_author", "author_id"),
        Index("idx_ingest_posts_category", "category"),
        Index("idx_ingest_posts_created", "created_at"),
    )


class IngestAttachment(Base):
    __tablename__ = "ingest_attachments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ingest_posts.id", name="fk_ingest_attachments_post", ondelete="CASCADE"),
        nullable=False,
    )
    stored_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ocr_text: Mapped[Optional[str]] = mapped_column(MEDIUMTEXT, nullable=True)
    ocr_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ocr_done_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), nullable=False
    )

    __table_args__ = (Index("idx_ingest_attachments_post", "post_id"),)


class IngestJob(Base):
    __tablename__ = "ingest_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ingest_posts.id", name="fk_ingest_jobs_post", ondelete="CASCADE"),
        nullable=False,
    )
    stage: Mapped[IngestJobStage] = mapped_column(
        Enum(IngestJobStage, name="ingest_job_stage"), nullable=False
    )
    status: Mapped[IngestJobStatus] = mapped_column(
        Enum(IngestJobStatus, name="ingest_job_status"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    log_text: Mapped[Optional[str]] = mapped_column(MEDIUMTEXT, nullable=True)
    error_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_ingest_jobs_post", "post_id"),
        Index("idx_ingest_jobs_started", "started_at"),
    )
