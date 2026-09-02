from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SampleStatus


class SampleIdSequence(Base):
    __tablename__ = "sample_id_sequences"

    year: Mapped[int] = mapped_column(primary_key=True)
    next_value: Mapped[int] = mapped_column(nullable=False, default=1)


class Sample(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "samples"
    __table_args__ = (
        CheckConstraint("quantity_original > 0", name="ck_sample_qty_original_positive"),
        CheckConstraint("quantity_remaining >= 0", name="ck_sample_qty_remaining_nonneg"),
    )

    sample_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=SampleStatus.RECEIVED, index=True)
    sample_type: Mapped[str] = mapped_column(String(100), nullable=False)
    material_type: Mapped[str | None] = mapped_column(String(100))
    quantity_original: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_remaining: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(16), nullable=False)
    collection_date: Mapped[date | None] = mapped_column(Date)
    received_date: Mapped[date | None] = mapped_column(Date)
    source_location: Mapped[str | None] = mapped_column(String(255))
    temperature_requirement: Mapped[str | None] = mapped_column(String(64))
    restriction_flag: Mapped[bool] = mapped_column(default=False, nullable=False)
    shipment_id: Mapped[UUID | None] = mapped_column(ForeignKey("shipments.id"), index=True)
    current_storage_location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("storage_locations.id"), nullable=True
    )
    current_custodian_id: Mapped[UUID | None] = mapped_column(ForeignKey("custodians.id"), nullable=True)
    accessioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    accessioned_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    identifiers: Mapped[list["SampleIdentifier"]] = relationship(back_populates="sample")
    aliases: Mapped[list["SampleAlias"]] = relationship(back_populates="sample")
    shipment: Mapped["Shipment | None"] = relationship(back_populates="samples")
    current_storage_location: Mapped["StorageLocation | None"] = relationship(
        foreign_keys=[current_storage_location_id]
    )
    current_custodian: Mapped["Custodian | None"] = relationship(foreign_keys=[current_custodian_id])
    labels: Mapped[list["SampleLabel"]] = relationship(back_populates="sample")


class SampleIdentifier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sample_identifiers"
    __table_args__ = (UniqueConstraint("identifier_type", "value", name="uq_sample_identifier_type_value"),)

    sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    identifier_type: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    sample: Mapped[Sample] = relationship(back_populates="identifiers")


class SampleAlias(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sample_aliases"
    __table_args__ = (UniqueConstraint("alias_type", "value", name="uq_sample_alias_type_value"),)

    sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    alias_type: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    sample: Mapped[Sample] = relationship(back_populates="aliases")
