from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin


class SampleLabel(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "sample_labels"

    sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    label_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    barcode_format: Mapped[str] = mapped_column(String(32), default="code128", nullable=False)
    png_storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    pdf_storage_key: Mapped[str | None] = mapped_column(String(512))
    print_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    sample: Mapped["Sample"] = relationship(back_populates="labels")
    print_events: Mapped[list["LabelPrintEvent"]] = relationship(back_populates="label")


class LabelPrintEvent(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "label_print_events"

    label_id: Mapped[UUID] = mapped_column(ForeignKey("sample_labels.id"), nullable=False, index=True)
    sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_reprint: Mapped[bool] = mapped_column(default=False, nullable=False)

    label: Mapped[SampleLabel] = relationship(back_populates="print_events")
