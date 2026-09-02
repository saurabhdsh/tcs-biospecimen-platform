from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import ActorMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ManifestStatus


class Manifest(UUIDPrimaryKeyMixin, TimestampMixin, ActorMixin, Base):
    __tablename__ = "manifests"

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default=ManifestStatus.UPLOADED, nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    column_mapping: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    committed_shipment_id: Mapped[UUID | None] = mapped_column(ForeignKey("shipments.id"), nullable=True)

    files: Mapped[list["ManifestFile"]] = relationship(back_populates="manifest")
    rows: Mapped[list["ManifestRow"]] = relationship(back_populates="manifest")
    validation_errors: Mapped[list["ManifestValidationError"]] = relationship(back_populates="manifest")


class ManifestFile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manifest_files"

    manifest_id: Mapped[UUID] = mapped_column(ForeignKey("manifests.id"), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128))

    manifest: Mapped[Manifest] = relationship(back_populates="files")


class ManifestRow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manifest_rows"
    __table_args__ = (UniqueConstraint("manifest_id", "row_number", name="uq_manifest_row_number"),)

    manifest_id: Mapped[UUID] = mapped_column(ForeignKey("manifests.id"), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    canonical_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_valid: Mapped[bool | None] = mapped_column(nullable=True)
    committed_sample_id: Mapped[UUID | None] = mapped_column(ForeignKey("samples.id"), nullable=True)

    manifest: Mapped[Manifest] = relationship(back_populates="rows")
    errors: Mapped[list["ManifestValidationError"]] = relationship(back_populates="row")


class ManifestValidationError(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "manifest_validation_errors"

    manifest_id: Mapped[UUID] = mapped_column(ForeignKey("manifests.id"), nullable=False, index=True)
    row_id: Mapped[UUID | None] = mapped_column(ForeignKey("manifest_rows.id"), nullable=True)
    row_number: Mapped[int | None] = mapped_column(Integer)
    field_name: Mapped[str | None] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    manifest: Mapped[Manifest] = relationship(back_populates="validation_errors")
    row: Mapped[ManifestRow | None] = relationship(back_populates="errors")
