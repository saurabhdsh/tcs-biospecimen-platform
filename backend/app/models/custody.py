from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Custodian(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "custodians"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    assignments: Mapped[list["CustodyAssignment"]] = relationship(back_populates="custodian")


class CustodyAssignment(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "custody_assignments"

    sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    custodian_id: Mapped[UUID] = mapped_column(ForeignKey("custodians.id"), nullable=False, index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_primary: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text)

    custodian: Mapped[Custodian] = relationship(back_populates="assignments")
    sample: Mapped["Sample"] = relationship()


class CustodyEvent(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "custody_events"

    sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text)
    previous_location_id: Mapped[UUID | None] = mapped_column(ForeignKey("storage_locations.id"))
    destination_location_id: Mapped[UUID | None] = mapped_column(ForeignKey("storage_locations.id"))
    checked_out_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    elapsed_seconds: Mapped[int | None] = mapped_column()
    is_open: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)

    sample: Mapped["Sample"] = relationship()
