import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Enum,
    ForeignKey,
    Index,
    String,
    TIMESTAMP,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WikiPageSourceRelation(str, enum.Enum):
    created = "created"
    updated = "updated"


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    current_commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    last_ingest_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    __table_args__ = (Index("idx_wiki_pages_category", "category"),)


class WikiPageSource(Base):
    __tablename__ = "wiki_page_sources"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    wiki_page_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("wiki_pages.id", name="fk_wps_page", ondelete="CASCADE"),
        nullable=False,
    )
    ingest_post_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ingest_posts.id", name="fk_wps_post", ondelete="CASCADE"),
        nullable=False,
    )
    relation: Mapped[WikiPageSourceRelation] = mapped_column(
        Enum(WikiPageSourceRelation, name="wiki_page_source_relation"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), nullable=False
    )

    __table_args__ = (
        Index("idx_wps_page", "wiki_page_id"),
        Index("idx_wps_post", "ingest_post_id"),
    )


class WikiBacklink(Base):
    __tablename__ = "wiki_backlinks"

    from_page_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("wiki_pages.id", name="fk_wbl_from", ondelete="CASCADE"),
        primary_key=True,
    )
    to_page_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("wiki_pages.id", name="fk_wbl_to", ondelete="CASCADE"),
        primary_key=True,
    )

    __table_args__ = (Index("idx_wbl_to", "to_page_id"),)
