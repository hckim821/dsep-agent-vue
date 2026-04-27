from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Index, String, TIMESTAMP, func
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SchemaVersion(Base):
    __tablename__ = "schema_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(MEDIUMTEXT, nullable=False)
    updated_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", name="fk_schema_versions_user"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), nullable=False
    )
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (Index("idx_schema_versions_updated", "updated_at"),)
