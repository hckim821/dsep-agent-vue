import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Enum,
    ForeignKey,
    Index,
    TIMESTAMP,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class LintFindingType(str, enum.Enum):
    contradiction = "contradiction"
    orphan = "orphan"
    stale = "stale"
    missing_entity = "missing_entity"
    broken_link = "broken_link"


class LintFindingSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class LintFinding(Base):
    __tablename__ = "lint_findings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    type: Mapped[LintFindingType] = mapped_column(
        Enum(LintFindingType, name="lint_finding_type"), nullable=False
    )
    page_ids_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[LintFindingSeverity] = mapped_column(
        Enum(LintFindingSeverity, name="lint_finding_severity"),
        nullable=False,
        default=LintFindingSeverity.medium,
    )
    detected_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), nullable=False
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP, nullable=True)
    resolved_by_post_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("ingest_posts.id", name="fk_lint_findings_post", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_lint_findings_type_resolved", "type", "resolved_at"),
        Index("idx_lint_findings_severity", "severity"),
    )
