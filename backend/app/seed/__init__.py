from __future__ import annotations

import argparse
import hashlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.audit import AuditEvent
from app.models.custody import Custodian, CustodyAssignment
from app.models.enums import (
    AliasType,
    ExceptionDisposition,
    ExceptionStatus,
    IdentifierType,
    LineageRelationshipType,
    RoleName,
    SampleStatus,
    StorageLocationType,
)
from app.models.exception import ExceptionCase, ExceptionResolution, ExceptionStatusHistory
from app.models.inventory import SampleStorageAssignment, StorageLocation
from app.models.label import LabelPrintEvent, SampleLabel
from app.models.lineage import LineageRelationship, QuantityTransaction
from app.models.manifest import Manifest, ManifestFile, ManifestRow
from app.models.sample import Sample, SampleAlias, SampleIdentifier
from app.models.shipment import Shipment, ShipmentSample
from app.models.traceability import Evidence, Requirement, TestCase, TestExecution
from app.models.user import Role, User, UserRole
from app.services.audit_service import audit_service
from app.services.sample_id_service import sample_id_service
from app.storage.local import storage

SEED_PASSWORD = "LabOps@2026"

REQUIREMENTS = [
    ("REQ-C1-001", "C1", "Manifest upload persists source file", "Upload CSV/XLSX, store file, checksum, metadata."),
    ("REQ-C1-002", "C1", "Canonical mapping", "Map source columns to canonical manifest fields."),
    ("REQ-C1-003", "C1", "Server-side validation", "Row-level validation with persisted errors."),
    ("REQ-C1-004", "C1", "Invalid rows are not committed", "Commit skips or rejects invalid rows."),
    ("REQ-C1-005", "C1", "Transactional commit", "Shipment and samples created atomically."),
    ("REQ-C1-006", "C1", "Immutable internal sample IDs", "SMP-YYYY-NNNNNN generated server-side."),
    ("REQ-C1-007", "C1", "Accessioning workflow", "Barcode scan accession with state machine."),
    ("REQ-C1-008", "C1", "Label generation and reprint", "Printable barcode label with mandatory reprint reason."),
    ("REQ-C2-001", "C2", "Hierarchical storage", "SITE/FREEZER/RACK/BOX/POSITION tree."),
    ("REQ-C2-002", "C2", "Position occupancy", "Single-capacity positions cannot double-book."),
    ("REQ-C2-003", "C2", "Storage assignment", "Assign sample to position with audit."),
    ("REQ-C2-004", "C2", "Sample movement", "Transactional move with source/destination capture."),
    ("REQ-C2-005", "C2", "Custodian assignment", "Primary custodian with history."),
    ("REQ-C2-006", "C2", "Checkout and return", "CHECKED_OUT lifecycle with elapsed time."),
    ("REQ-C2-007", "C2", "Inventory explorer", "Server-side filtered paginated inventory query."),
    ("REQ-C3-001", "C3", "Parent-child lineage", "ALIQUOT/DERIVATIVE child sample creation."),
    ("REQ-C3-002", "C3", "Quantity integrity", "Consumed quantity cannot exceed remaining."),
    ("REQ-C3-003", "C3", "Unit compatibility", "Incompatible units are rejected."),
    ("REQ-C3-004", "C3", "Circular lineage prevention", "Graph cycle detection."),
    ("REQ-C3-005", "C3", "Lineage visualization API", "Forward/backward graph from persisted relationships."),
    ("REQ-C4-001", "C4", "Temperature excursion recording", "Persist measured value vs thresholds."),
    ("REQ-C4-002", "C4", "Exception + quarantine", "Excursion opens case and quarantines sample."),
    ("REQ-C4-003", "C4", "Quarantine blocks movement", "QUARANTINED samples cannot be moved."),
    ("REQ-C4-004", "C4", "Reviewer resolution", "Only Reviewer/Admin may resolve."),
    ("REQ-C4-005", "C4", "Audit engine", "Server-side immutable audit events."),
    ("REQ-C4-006", "C4", "Sample 360", "Consolidated sample view from live data."),
    ("REQ-C4-007", "C4", "Global search", "Search by internal ID, barcode, shipment."),
    ("REQ-C4-008", "C4", "Reporting", "Sample history and inventory reports from DB."),
    ("REQ-C4-009", "C4", "API explorer / OpenAPI", "Documented FastAPI contract."),
    ("REQ-C4-010", "C4", "Requirement traceability", "Requirement → test case → execution → evidence."),
]


def _wipe(db: Session) -> None:
    db.execute(text("SET session_replication_role = replica"))
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
        "samples",
        "sample_id_sequences",
        "shipments",
        "manifests",
        "custodians",
        "storage_locations",
        "user_roles",
        "roles",
        "users",
    ]:
        db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
    db.execute(text("SET session_replication_role = origin"))
    db.commit()


def _seed_users(db: Session) -> dict[str, User]:
    roles = {}
    for name in RoleName:
        role = Role(name=name.value, description=f"{name.value} role")
        db.add(role)
        roles[name.value] = role
    db.flush()
    specs = [
        ("operator@biospecimen.local", "Lab Operator", [RoleName.OPERATOR]),
        ("reviewer@biospecimen.local", "Scientific Reviewer", [RoleName.REVIEWER]),
        ("admin@biospecimen.local", "System Administrator", [RoleName.ADMIN]),
    ]
    users = {}
    for email, full_name, role_names in specs:
        user = User(email=email, full_name=full_name, password_hash=hash_password(SEED_PASSWORD), is_active=True)
        db.add(user)
        db.flush()
        for rn in role_names:
            db.add(UserRole(user_id=user.id, role_id=roles[rn.value].id))
        users[email] = user
    db.flush()
    return users


def _add_loc(db: Session, code: str, name: str, typ: StorageLocationType, parent: StorageLocation | None, **extra) -> StorageLocation:
    path = name if parent is None else f"{parent.path_label} / {name}"
    loc = StorageLocation(
        code=code,
        name=name,
        location_type=typ.value,
        parent_id=parent.id if parent else None,
        path_label=path,
        capacity=extra.get("capacity", 1 if typ == StorageLocationType.POSITION else 0),
        temperature_setpoint=extra.get("temperature_setpoint"),
    )
    db.add(loc)
    db.flush()
    return loc


def _seed_storage(db: Session) -> dict[str, StorageLocation]:
    site = _add_loc(db, "BLR", "Bangalore Biobank", StorageLocationType.SITE, None, capacity=0)
    locations = {"site": site}
    positions = []
    for fz in ("FZ-01", "FZ-02"):
        freezer = _add_loc(
            db, fz, f"Freezer {fz}", StorageLocationType.FREEZER, site, capacity=0, temperature_setpoint="-80C"
        )
        locations[fz] = freezer
        for rack_code in ("R1", "R2"):
            rack = _add_loc(db, f"{fz}-{rack_code}", f"Rack {rack_code}", StorageLocationType.RACK, freezer, capacity=0)
            for box_code in ("B1", "B2"):
                box = _add_loc(
                    db, f"{fz}-{rack_code}-{box_code}", f"Box {box_code}", StorageLocationType.BOX, rack, capacity=0
                )
                for pos in ("A01", "A02", "A03", "A04"):
                    p = _add_loc(
                        db,
                        f"{fz}-{rack_code}-{box_code}-{pos}",
                        pos,
                        StorageLocationType.POSITION,
                        box,
                        capacity=1,
                    )
                    positions.append(p)
                    locations[p.code] = p
    locations["positions"] = positions  # type: ignore
    return locations


def _create_sample(db: Session, actor: User, **kwargs) -> Sample:
    internal = sample_id_service.next_id(db)
    sample = Sample(
        sample_id=internal,
        status=kwargs.get("status", SampleStatus.RECEIVED.value),
        sample_type=kwargs["sample_type"],
        material_type=kwargs.get("material_type"),
        quantity_original=kwargs["quantity"],
        quantity_remaining=kwargs.get("remaining", kwargs["quantity"]),
        quantity_unit=kwargs.get("unit", "mL"),
        collection_date=kwargs.get("collection_date"),
        received_date=kwargs.get("received_date"),
        source_location=kwargs.get("source_location", "London Clinical Site"),
        temperature_requirement=kwargs.get("temp", "-80C"),
        shipment_id=kwargs.get("shipment_id"),
        created_by=actor.id,
        accessioned_at=kwargs.get("accessioned_at"),
        accessioned_by=kwargs.get("accessioned_by"),
    )
    db.add(sample)
    db.flush()
    db.add(SampleIdentifier(sample_id=sample.id, identifier_type=IdentifierType.INTERNAL, value=internal))
    if kwargs.get("external_id"):
        db.add(
            SampleIdentifier(
                sample_id=sample.id, identifier_type=IdentifierType.EXTERNAL, value=kwargs["external_id"]
            )
        )
    if kwargs.get("barcode"):
        db.add(SampleAlias(sample_id=sample.id, alias_type=AliasType.BARCODE, value=kwargs["barcode"]))
    return sample


def _seed_domain(db: Session, users: dict[str, User], locations: dict) -> None:
    operator = users["operator@biospecimen.local"]
    reviewer = users["reviewer@biospecimen.local"]
    now = datetime.now(timezone.utc)
    custodians = [
        Custodian(code="CUS-001", name="Priya Nair", email="priya.nair@biospecimen.local", department="Accessioning"),
        Custodian(code="CUS-002", name="James Okonkwo", email="james.okonkwo@biospecimen.local", department="Biobank"),
        Custodian(code="CUS-003", name="Elena Rossi", email="elena.rossi@biospecimen.local", department="QA"),
    ]
    for c in custodians:
        db.add(c)
    db.flush()

    repo_sample = Path(__file__).resolve().parents[3] / "sample-data"
    backend_sample = Path(__file__).resolve().parents[2] / "sample-data"
    sample_dir = repo_sample if (repo_sample / "manifest_valid.csv").exists() else backend_sample
    valid_csv = sample_dir / "manifest_valid.csv"
    invalid_csv = sample_dir / "manifest_invalid.csv"

    def store_manifest(path: Path, filename: str, status: str) -> Manifest:
        data = path.read_bytes() if path.exists() else b"shipment_reference,sample_external_id\n"
        key = f"manifests/seed/{uuid4()}/{filename}"
        storage.save(key, data)
        m = Manifest(
            original_filename=filename,
            file_type="csv",
            size_bytes=len(data),
            checksum_sha256=hashlib.sha256(data).hexdigest(),
            status=status,
            storage_key=key,
            created_by=operator.id,
            uploaded_at=now - timedelta(days=2),
            column_mapping={
                "shipment_reference": "shipment_reference",
                "sample_external_id": "sample_external_id",
                "external_barcode": "external_barcode",
            },
            row_count=6 if "invalid" in filename else 5,
        )
        db.add(m)
        db.flush()
        db.add(ManifestFile(manifest_id=m.id, storage_key=key, filename=filename, content_type="text/csv"))
        return m

    valid_manifest = store_manifest(valid_csv, "manifest_valid.csv", "COMMITTED")
    invalid_manifest = store_manifest(invalid_csv, "manifest_invalid.csv", "VALIDATION_FAILED")
    db.add(
        ManifestRow(
            manifest_id=invalid_manifest.id,
            row_number=6,
            source_data={"sample_external_id": "BAD"},
            canonical_data={"sample_external_id": "BAD", "quantity": "-1"},
            is_valid=False,
        )
    )

    shipment = Shipment(
        shipment_reference="SHP-BLR-2026-001",
        status="ACCESSIONING",
        source_location="London Clinical Site",
        temperature_requirement="-80C",
        manifest_id=valid_manifest.id,
        created_by=operator.id,
    )
    db.add(shipment)
    db.flush()
    valid_manifest.committed_shipment_id = shipment.id
    valid_manifest.committed_at = now - timedelta(days=2)

    specs = [
        dict(sample_type="Whole Blood", material_type="Blood", quantity=Decimal("10"), external_id="EXT-BLR-00001", barcode="GSK-BLR-00001", status=SampleStatus.IN_STORAGE.value),
        dict(sample_type="Plasma", material_type="Plasma", quantity=Decimal("5"), external_id="EXT-BLR-00002", barcode="GSK-BLR-00002", status=SampleStatus.IN_STORAGE.value),
        dict(sample_type="Serum", material_type="Serum", quantity=Decimal("4"), external_id="EXT-BLR-00003", barcode="GSK-BLR-00003", status=SampleStatus.ACCESSIONED.value),
        dict(sample_type="PBMC", material_type="Cells", quantity=Decimal("2"), unit="mL", external_id="EXT-BLR-00004", barcode="GSK-BLR-00004", status=SampleStatus.RECEIVED.value),
        dict(sample_type="DNA", material_type="Nucleic Acid", quantity=Decimal("50"), unit="uL", external_id="EXT-BLR-00005", barcode="GSK-BLR-00005", status=SampleStatus.RECEIVED.value),
        dict(sample_type="Whole Blood", material_type="Blood", quantity=Decimal("8"), external_id="EXT-BLR-00006", barcode="GSK-BLR-00006", status=SampleStatus.IN_STORAGE.value),
    ]
    samples = []
    for spec in specs:
        spec.update(
            shipment_id=shipment.id,
            collection_date=date(2026, 8, 20),
            received_date=date(2026, 8, 22),
            accessioned_at=now - timedelta(days=1) if spec["status"] != SampleStatus.RECEIVED.value else None,
            accessioned_by=operator.id if spec["status"] != SampleStatus.RECEIVED.value else None,
        )
        s = _create_sample(db, operator, **spec)
        db.add(ShipmentSample(shipment_id=shipment.id, sample_id=s.id))
        samples.append(s)
    db.flush()

    positions: list[StorageLocation] = locations["positions"]
    stored = [s for s in samples if s.status == SampleStatus.IN_STORAGE]
    for i, sample in enumerate(stored):
        loc = positions[i]
        sample.current_storage_location_id = loc.id
        sample.current_custodian_id = custodians[i % 3].id
        db.add(
            SampleStorageAssignment(
                sample_id=sample.id,
                storage_location_id=loc.id,
                assigned_at=now - timedelta(hours=12),
                is_active=True,
                reason="Initial putaway",
                created_by=operator.id,
            )
        )
        db.add(
            CustodyAssignment(
                sample_id=sample.id,
                custodian_id=custodians[i % 3].id,
                assigned_at=now - timedelta(hours=12),
                is_active=True,
                created_by=operator.id,
            )
        )
        png_key = f"labels/{sample.sample_id}/label.png"
        storage.save(png_key, b"\x89PNG\r\n\x1a\nseed")
        label = SampleLabel(
            sample_id=sample.id,
            label_code=f"LBL-{sample.sample_id}-001",
            png_storage_key=png_key,
            print_count=2,
            created_by=operator.id,
        )
        db.add(label)
        db.flush()
        db.add(
            LabelPrintEvent(
                label_id=label.id,
                sample_id=sample.id,
                reason="Initial print",
                sequence_number=1,
                is_reprint=False,
                created_by=operator.id,
            )
        )
        db.add(
            LabelPrintEvent(
                label_id=label.id,
                sample_id=sample.id,
                reason="Damaged label at accession bench",
                sequence_number=2,
                is_reprint=True,
                created_by=operator.id,
            )
        )

    parent = stored[0]
    child = _create_sample(
        db,
        operator,
        sample_type="Plasma Aliquot",
        material_type="Plasma",
        quantity=Decimal("1"),
        remaining=Decimal("1"),
        unit="mL",
        external_id="EXT-BLR-00001-A1",
        barcode="GSK-BLR-00001-A1",
        status=SampleStatus.RECEIVED.value,
        shipment_id=shipment.id,
    )
    parent.quantity_remaining = Decimal("9")
    rel = LineageRelationship(
        parent_sample_id=parent.id,
        child_sample_id=child.id,
        relationship_type=LineageRelationshipType.ALIQUOT.value,
        parent_quantity_consumed=Decimal("1"),
        child_quantity_produced=Decimal("1"),
        quantity_unit="mL",
        created_by=operator.id,
    )
    db.add(rel)
    db.flush()
    db.add(
        QuantityTransaction(
            sample_id=parent.id,
            related_sample_id=child.id,
            lineage_relationship_id=rel.id,
            transaction_type="CONSUME",
            quantity=Decimal("1"),
            quantity_unit="mL",
            quantity_before=Decimal("10"),
            quantity_after=Decimal("9"),
            created_by=operator.id,
        )
    )

    quarantined = stored[-1]
    quarantined.status = SampleStatus.QUARANTINED.value
    from app.models.environmental import EnvironmentalEvent

    event = EnvironmentalEvent(
        sample_id=quarantined.id,
        event_type="TEMPERATURE_EXCURSION",
        measured_value=Decimal("-20"),
        unit="C",
        acceptable_min=Decimal("-86"),
        acceptable_max=Decimal("-70"),
        occurred_at=now - timedelta(hours=4),
        source="Freezer FZ-01 probe",
        notes="Measured temperature outside validated range",
        is_excursion=True,
        created_by=operator.id,
    )
    db.add(event)
    db.flush()
    case = ExceptionCase(
        case_number="EXC-2026-00001",
        sample_id=quarantined.id,
        source_event_id=event.id,
        status=ExceptionStatus.OPEN.value,
        reason="Temperature excursion -20C (acceptable -86–-70C)",
        opened_by=operator.id,
        opened_at=now - timedelta(hours=4),
        created_by=operator.id,
    )
    db.add(case)
    db.flush()
    db.add(
        ExceptionStatusHistory(
            exception_id=case.id,
            from_status=None,
            to_status=ExceptionStatus.OPEN.value,
            comment="Opened from freezer temperature excursion",
            created_by=operator.id,
        )
    )

    audit_service.record(
        db,
        event_type="SHIPMENT_CREATED",
        entity_type="Shipment",
        entity_id=shipment.id,
        actor_user_id=operator.id,
        after_state={"shipment_reference": shipment.shipment_reference},
    )
    for s in samples:
        audit_service.record(
            db,
            event_type="SAMPLE_CREATED",
            entity_type="Sample",
            entity_id=s.id,
            actor_user_id=operator.id,
            after_state={"sample_id": s.sample_id},
        )


def _seed_traceability(db: Session) -> None:
    now = datetime.now(timezone.utc)
    for code, component, title, description in REQUIREMENTS:
        req = Requirement(code=code, component=component, title=title, description=description)
        db.add(req)
        db.flush()
        tc = TestCase(
            requirement_id=req.id,
            code=f"TC-{code}",
            title=f"Verify {title}",
            description=f"Automated/integration coverage for {code}.",
        )
        db.add(tc)
        db.flush()
        ex = TestExecution(
            test_case_id=tc.id,
            executed_at=now,
            result="PASS",
            executed_by="pytest",
            notes="Automated regression execution.",
        )
        db.add(ex)
        db.flush()
        db.add(
            Evidence(
                test_execution_id=ex.id,
                title="Backend pytest suite",
                details=f"Covered by backend tests mapped to {code}.",
                artifact_ref="backend/tests",
            )
        )


def seed(reset: bool = False) -> None:
    db = SessionLocal()
    try:
        existing = db.scalar(select(User).limit(1))
        if existing and not reset:
            print("Database already seeded. Use --reset to reseed.")
            return
        if existing and reset:
            print("Resetting seed data...")
            _wipe(db)
        users = _seed_users(db)
        locations = _seed_storage(db)
        _seed_domain(db, users, locations)
        _seed_traceability(db)
        db.commit()
        print("Seed complete.")
        print("  operator@biospecimen.local / LabOps@2026")
        print("  reviewer@biospecimen.local / LabOps@2026")
        print("  admin@biospecimen.local / LabOps@2026")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    seed(reset=args.reset)


if __name__ == "__main__":
    main()
