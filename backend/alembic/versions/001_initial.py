"""Initial schema for TCS Biospecimen Platform.

Revision ID: 001_initial
Revises:
Create Date: 2026-09-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "user_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    op.create_table(
        "storage_locations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location_type", sa.String(32), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("temperature_setpoint", sa.String(32), nullable=True),
        sa.Column("path_label", sa.String(512), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["storage_locations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "code", name="uq_storage_code_per_parent"),
    )
    op.create_index("ix_storage_locations_code", "storage_locations", ["code"])
    op.create_index("ix_storage_locations_location_type", "storage_locations", ["location_type"])
    op.create_index("ix_storage_locations_parent_id", "storage_locations", ["parent_id"])

    op.create_table(
        "custodians",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("department", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "manifests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(16), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="UPLOADED"),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("column_mapping", postgresql.JSONB(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invalid_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("committed_shipment_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manifests_checksum_sha256", "manifests", ["checksum_sha256"])
    op.create_index("ix_manifests_status", "manifests", ["status"])

    op.create_table(
        "shipments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shipment_reference", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="RECEIVED"),
        sa.Column("source_location", sa.String(255), nullable=True),
        sa.Column("temperature_requirement", sa.String(64), nullable=True),
        sa.Column("manifest_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["manifest_id"], ["manifests.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_reference"),
    )
    op.create_index("ix_shipments_shipment_reference", "shipments", ["shipment_reference"])

    op.create_foreign_key(
        "fk_manifests_committed_shipment_id",
        "manifests",
        "shipments",
        ["committed_shipment_id"],
        ["id"],
    )

    op.create_table(
        "samples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="RECEIVED"),
        sa.Column("sample_type", sa.String(100), nullable=False),
        sa.Column("material_type", sa.String(100), nullable=True),
        sa.Column("quantity_original", sa.Numeric(18, 6), nullable=False),
        sa.Column("quantity_remaining", sa.Numeric(18, 6), nullable=False),
        sa.Column("quantity_unit", sa.String(16), nullable=False),
        sa.Column("collection_date", sa.Date(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("source_location", sa.String(255), nullable=True),
        sa.Column("temperature_requirement", sa.String(64), nullable=True),
        sa.Column("restriction_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("shipment_id", sa.Uuid(), nullable=True),
        sa.Column("current_storage_location_id", sa.Uuid(), nullable=True),
        sa.Column("current_custodian_id", sa.Uuid(), nullable=True),
        sa.Column("accessioned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accessioned_by", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity_original > 0", name="ck_sample_qty_original_positive"),
        sa.CheckConstraint("quantity_remaining >= 0", name="ck_sample_qty_remaining_nonneg"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"]),
        sa.ForeignKeyConstraint(["current_storage_location_id"], ["storage_locations.id"]),
        sa.ForeignKeyConstraint(["current_custodian_id"], ["custodians.id"]),
        sa.ForeignKeyConstraint(["accessioned_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sample_id"),
    )
    op.create_index("ix_samples_sample_id", "samples", ["sample_id"])
    op.create_index("ix_samples_status", "samples", ["status"])
    op.create_index("ix_samples_shipment_id", "samples", ["shipment_id"])

    op.create_table(
        "sample_id_sequences",
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("next_value", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("year"),
    )

    op.create_table(
        "sample_identifiers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("identifier_type", sa.String(32), nullable=False),
        sa.Column("value", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identifier_type", "value", name="uq_sample_identifier_type_value"),
    )
    op.create_index("ix_sample_identifiers_sample_id", "sample_identifiers", ["sample_id"])
    op.create_index("ix_sample_identifiers_value", "sample_identifiers", ["value"])

    op.create_table(
        "sample_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("alias_type", sa.String(32), nullable=False),
        sa.Column("value", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alias_type", "value", name="uq_sample_alias_type_value"),
    )
    op.create_index("ix_sample_aliases_sample_id", "sample_aliases", ["sample_id"])
    op.create_index("ix_sample_aliases_value", "sample_aliases", ["value"])

    op.create_table(
        "shipment_samples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shipment_id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"]),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_id", "sample_id", name="uq_shipment_sample"),
    )

    op.create_table(
        "manifest_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("manifest_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["manifest_id"], ["manifests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manifest_files_manifest_id", "manifest_files", ["manifest_id"])

    op.create_table(
        "manifest_rows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("manifest_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("source_data", postgresql.JSONB(), nullable=False),
        sa.Column("canonical_data", postgresql.JSONB(), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=True),
        sa.Column("committed_sample_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["manifest_id"], ["manifests.id"]),
        sa.ForeignKeyConstraint(["committed_sample_id"], ["samples.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manifest_id", "row_number", name="uq_manifest_row_number"),
    )
    op.create_index("ix_manifest_rows_manifest_id", "manifest_rows", ["manifest_id"])

    op.create_table(
        "manifest_validation_errors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("manifest_id", sa.Uuid(), nullable=False),
        sa.Column("row_id", sa.Uuid(), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("field_name", sa.String(64), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["manifest_id"], ["manifests.id"]),
        sa.ForeignKeyConstraint(["row_id"], ["manifest_rows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manifest_validation_errors_manifest_id", "manifest_validation_errors", ["manifest_id"])

    op.create_table(
        "sample_labels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("label_code", sa.String(64), nullable=False),
        sa.Column("barcode_format", sa.String(32), nullable=False, server_default="code128"),
        sa.Column("png_storage_key", sa.String(512), nullable=False),
        sa.Column("pdf_storage_key", sa.String(512), nullable=True),
        sa.Column("print_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("label_code"),
    )
    op.create_index("ix_sample_labels_sample_id", "sample_labels", ["sample_id"])

    op.create_table(
        "label_print_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("label_id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("is_reprint", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["label_id"], ["sample_labels.id"]),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_label_print_events_label_id", "label_print_events", ["label_id"])
    op.create_index("ix_label_print_events_sample_id", "label_print_events", ["sample_id"])

    op.create_table(
        "sample_storage_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("storage_location_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["storage_location_id"], ["storage_locations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ssa_sample_id", "sample_storage_assignments", ["sample_id"])
    op.create_index("ix_ssa_storage_location_id", "sample_storage_assignments", ["storage_location_id"])
    op.create_index("ix_ssa_is_active", "sample_storage_assignments", ["is_active"])
    op.execute(
        """
        CREATE UNIQUE INDEX uq_active_position_occupancy
        ON sample_storage_assignments (storage_location_id)
        WHERE is_active = true
        """
    )

    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("transaction_type", sa.String(32), nullable=False),
        sa.Column("source_location_id", sa.Uuid(), nullable=True),
        sa.Column("destination_location_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["source_location_id"], ["storage_locations.id"]),
        sa.ForeignKeyConstraint(["destination_location_id"], ["storage_locations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_transactions_sample_id", "inventory_transactions", ["sample_id"])

    op.create_table(
        "custody_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("custodian_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["custodian_id"], ["custodians.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_custody_assignments_sample_id", "custody_assignments", ["sample_id"])
    op.create_index("ix_custody_assignments_custodian_id", "custody_assignments", ["custodian_id"])
    op.create_index("ix_custody_assignments_is_active", "custody_assignments", ["is_active"])

    op.create_table(
        "custody_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("previous_location_id", sa.Uuid(), nullable=True),
        sa.Column("destination_location_id", sa.Uuid(), nullable=True),
        sa.Column("checked_out_by", sa.Uuid(), nullable=True),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=True),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["previous_location_id"], ["storage_locations.id"]),
        sa.ForeignKeyConstraint(["destination_location_id"], ["storage_locations.id"]),
        sa.ForeignKeyConstraint(["checked_out_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_custody_events_sample_id", "custody_events", ["sample_id"])
    op.create_index("ix_custody_events_is_open", "custody_events", ["is_open"])

    op.create_table(
        "lineage_relationships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_sample_id", sa.Uuid(), nullable=False),
        sa.Column("child_sample_id", sa.Uuid(), nullable=False),
        sa.Column("relationship_type", sa.String(32), nullable=False),
        sa.Column("parent_quantity_consumed", sa.Numeric(18, 6), nullable=False),
        sa.Column("child_quantity_produced", sa.Numeric(18, 6), nullable=False),
        sa.Column("quantity_unit", sa.String(16), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["child_sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_sample_id", "child_sample_id", name="uq_lineage_parent_child"),
        sa.CheckConstraint("parent_sample_id <> child_sample_id", name="ck_lineage_no_self_parent"),
        sa.CheckConstraint("parent_quantity_consumed > 0", name="ck_lineage_consumed_positive"),
        sa.CheckConstraint("child_quantity_produced > 0", name="ck_lineage_produced_positive"),
    )
    op.create_index("ix_lineage_parent_sample_id", "lineage_relationships", ["parent_sample_id"])
    op.create_index("ix_lineage_child_sample_id", "lineage_relationships", ["child_sample_id"])

    op.create_table(
        "quantity_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("related_sample_id", sa.Uuid(), nullable=True),
        sa.Column("lineage_relationship_id", sa.Uuid(), nullable=True),
        sa.Column("transaction_type", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("quantity_unit", sa.String(16), nullable=False),
        sa.Column("quantity_before", sa.Numeric(18, 6), nullable=False),
        sa.Column("quantity_after", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["related_sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["lineage_relationship_id"], ["lineage_relationships.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quantity_transactions_sample_id", "quantity_transactions", ["sample_id"])

    op.create_table(
        "environmental_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("measured_value", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit", sa.String(16), nullable=False),
        sa.Column("acceptable_min", sa.Numeric(12, 4), nullable=False),
        sa.Column("acceptable_max", sa.Numeric(12, 4), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_excursion", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_environmental_events_sample_id", "environmental_events", ["sample_id"])

    op.create_table(
        "exception_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_number", sa.String(32), nullable=False),
        sa.Column("sample_id", sa.Uuid(), nullable=False),
        sa.Column("source_event_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("opened_by", sa.Uuid(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"]),
        sa.ForeignKeyConstraint(["source_event_id"], ["environmental_events.id"]),
        sa.ForeignKeyConstraint(["opened_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_number"),
    )
    op.create_index("ix_exception_cases_case_number", "exception_cases", ["case_number"])
    op.create_index("ix_exception_cases_sample_id", "exception_cases", ["sample_id"])
    op.create_index("ix_exception_cases_status", "exception_cases", ["status"])

    op.create_table(
        "evidence_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("environmental_event_id", sa.Uuid(), nullable=True),
        sa.Column("exception_id", sa.Uuid(), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["environmental_event_id"], ["environmental_events.id"]),
        sa.ForeignKeyConstraint(["exception_id"], ["exception_cases.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_attachments_event_id", "evidence_attachments", ["environmental_event_id"])

    op.create_table(
        "exception_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exception_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["exception_id"], ["exception_cases.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_exception_status_history_exception_id", "exception_status_history", ["exception_id"])

    op.create_table(
        "exception_resolutions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exception_id", sa.Uuid(), nullable=False),
        sa.Column("resolver_user_id", sa.Uuid(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_comment", sa.Text(), nullable=False),
        sa.Column("disposition", sa.String(64), nullable=False),
        sa.Column("resulting_sample_status", sa.String(32), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["exception_id"], ["exception_cases.id"]),
        sa.ForeignKeyConstraint(["resolver_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exception_id"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("before_state", postgresql.JSONB(), nullable=True),
        sa.Column("after_state", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_entity", "audit_events", ["entity_type", "entity_id"])
    op.create_index("ix_audit_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_timestamp", "audit_events", ["timestamp"])
    op.create_index("ix_audit_actor", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_correlation_id", "audit_events", ["correlation_id"])

    op.create_table(
        "report_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_type", sa.String(64), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("criteria", postgresql.JSONB(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("csv_storage_key", sa.String(512), nullable=True),
        sa.Column("pdf_storage_key", sa.String(512), nullable=True),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_runs_report_type", "report_runs", ["report_type"])

    op.create_table(
        "requirements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("component", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_requirements_code", "requirements", ["code"])

    op.create_table(
        "test_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["requirement_id"], ["requirements.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requirement_id", "code", name="uq_testcase_per_requirement"),
    )
    op.create_index("ix_test_cases_requirement_id", "test_cases", ["requirement_id"])

    op.create_table(
        "test_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("executed_by", sa.String(128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_executions_test_case_id", "test_executions", ["test_case_id"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("test_execution_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("artifact_ref", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["test_execution_id"], ["test_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_test_execution_id", "evidence", ["test_execution_id"])


def downgrade() -> None:
    for table in [
        "evidence",
        "test_executions",
        "test_cases",
        "requirements",
        "report_runs",
        "audit_events",
        "exception_resolutions",
        "exception_status_history",
        "evidence_attachments",
        "exception_cases",
        "environmental_events",
        "quantity_transactions",
        "lineage_relationships",
        "custody_events",
        "custody_assignments",
        "inventory_transactions",
        "sample_storage_assignments",
        "label_print_events",
        "sample_labels",
        "manifest_validation_errors",
        "manifest_rows",
        "manifest_files",
        "shipment_samples",
        "sample_aliases",
        "sample_identifiers",
        "sample_id_sequences",
        "samples",
        "shipments",
        "manifests",
        "custodians",
        "storage_locations",
        "user_roles",
        "roles",
        "users",
    ]:
        op.drop_table(table)
