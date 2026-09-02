from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin


class EnvironmentalEvent(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "environmental_events"

    sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    measured_value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    acceptable_min: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    acceptable_max: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str | None] = mapped_column(String(128))
    notes: Mapped[str | None] = mapped_column(Text)
    is_excursion: Mapped[bool] = mapped_column(default=True, nullable=False)

    sample: Mapped["Sample"] = relationship()
    attachments: Mapped[list["EvidenceAttachment"]] = relationship(back_populates="environmental_event")
    exception_case: Mapped["ExceptionCase | None"] = relationship(back_populates="source_event")


class EvidenceAttachment(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "evidence_attachments"

    environmental_event_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("environmental_events.id"), nullable=True, index=True
    )
    exception_id: Mapped[UUID | None] = mapped_column(ForeignKey("exception_cases.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)

    environmental_event: Mapped[EnvironmentalEvent | None] = relationship(back_populates="attachments")
