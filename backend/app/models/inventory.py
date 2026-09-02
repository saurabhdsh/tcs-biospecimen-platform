from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import StorageLocationType


class StorageLocation(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "storage_locations"
    __table_args__ = (
        UniqueConstraint("parent_id", "code", name="uq_storage_code_per_parent"),
    )

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("storage_locations.id"), nullable=True, index=True)
    capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    temperature_setpoint: Mapped[str | None] = mapped_column(String(32))
    path_label: Mapped[str] = mapped_column(String(512), nullable=False)

    parent: Mapped["StorageLocation | None"] = relationship(
        remote_side="StorageLocation.id", back_populates="children"
    )
    children: Mapped[list["StorageLocation"]] = relationship(back_populates="parent")
    assignments: Mapped[list["SampleStorageAssignment"]] = relationship(back_populates="storage_location")

    @property
    def is_position(self) -> bool:
        return self.location_type == StorageLocationType.POSITION


class SampleStorageAssignment(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "sample_storage_assignments"

    sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    storage_location_id: Mapped[UUID] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=False, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)

    storage_location: Mapped[StorageLocation] = relationship(back_populates="assignments")
    sample: Mapped["Sample"] = relationship()


class InventoryTransaction(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "inventory_transactions"

    sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_location_id: Mapped[UUID | None] = mapped_column(ForeignKey("storage_locations.id"))
    destination_location_id: Mapped[UUID | None] = mapped_column(ForeignKey("storage_locations.id"))
    reason: Mapped[str | None] = mapped_column(Text)

    sample: Mapped["Sample"] = relationship()
