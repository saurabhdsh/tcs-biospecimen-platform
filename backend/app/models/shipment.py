from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ShipmentStatus


class Shipment(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "shipments"

    shipment_reference: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default=ShipmentStatus.RECEIVED, nullable=False)
    source_location: Mapped[str | None] = mapped_column(String(255))
    temperature_requirement: Mapped[str | None] = mapped_column(String(64))
    manifest_id: Mapped[UUID | None] = mapped_column(ForeignKey("manifests.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000))

    samples: Mapped[list["Sample"]] = relationship(back_populates="shipment")
    shipment_samples: Mapped[list["ShipmentSample"]] = relationship(back_populates="shipment")
    manifest: Mapped["Manifest | None"] = relationship(foreign_keys=[manifest_id])


class ShipmentSample(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shipment_samples"
    __table_args__ = (UniqueConstraint("shipment_id", "sample_id", name="uq_shipment_sample"),)

    shipment_id: Mapped[UUID] = mapped_column(ForeignKey("shipments.id"), nullable=False, index=True)
    sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)

    shipment: Mapped[Shipment] = relationship(back_populates="shipment_samples")
    sample: Mapped["Sample"] = relationship()
