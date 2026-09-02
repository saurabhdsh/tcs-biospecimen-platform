from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import UUIDPrimaryKeyMixin


class ReportRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "report_runs"

    report_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    requested_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    criteria: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    row_count: Mapped[int] = mapped_column(default=0, nullable=False)
    csv_storage_key: Mapped[str | None] = mapped_column(String(512))
    pdf_storage_key: Mapped[str | None] = mapped_column(String(512))
