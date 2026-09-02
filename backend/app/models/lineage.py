from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin


class LineageRelationship(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "lineage_relationships"
    __table_args__ = (
        UniqueConstraint("parent_sample_id", "child_sample_id", name="uq_lineage_parent_child"),
    )

    parent_sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    child_sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_quantity_consumed: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    child_quantity_produced: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(16), nullable=False)

    parent: Mapped["Sample"] = relationship(foreign_keys=[parent_sample_id])
    child: Mapped["Sample"] = relationship(foreign_keys=[child_sample_id])


class QuantityTransaction(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "quantity_transactions"

    sample_id: Mapped[UUID] = mapped_column(ForeignKey("samples.id"), nullable=False, index=True)
    related_sample_id: Mapped[UUID | None] = mapped_column(ForeignKey("samples.id"))
    lineage_relationship_id: Mapped[UUID | None] = mapped_column(ForeignKey("lineage_relationships.id"))
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity_before: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_after: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    sample: Mapped["Sample"] = relationship(foreign_keys=[sample_id])
