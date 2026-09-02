from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ExceptionStatus


class ExceptionCase(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "exception_cases"

    case_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    source_event_id: Mapped[UUID | None] = mapped_column(ForeignKey("environmental_events.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=ExceptionStatus.OPEN, nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    opened_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sample: Mapped["Sample"] = relationship()
    source_event: Mapped["EnvironmentalEvent | None"] = relationship(
        back_populates="exception_case", foreign_keys=[source_event_id]
    )
    status_history: Mapped[list["ExceptionStatusHistory"]] = relationship(back_populates="exception_case")
    resolution: Mapped["ExceptionResolution | None"] = relationship(back_populates="exception_case")


class ExceptionStatusHistory(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "exception_status_history"

    exception_id: Mapped[UUID] = mapped_column(ForeignKey("exception_cases.id"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    exception_case: Mapped[ExceptionCase] = relationship(back_populates="status_history")


class ExceptionResolution(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "exception_resolutions"

    exception_id: Mapped[UUID] = mapped_column(
        ForeignKey("exception_cases.id"), unique=True, nullable=False
    )
    resolver_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolution_comment: Mapped[str] = mapped_column(Text, nullable=False)
    disposition: Mapped[str] = mapped_column(String(64), nullable=False)
    resulting_sample_status: Mapped[str] = mapped_column(String(32), nullable=False)

    exception_case: Mapped[ExceptionCase] = relationship(back_populates="resolution")
