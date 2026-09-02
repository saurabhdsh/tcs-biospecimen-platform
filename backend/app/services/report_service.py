from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.models.audit import AuditEvent
from app.models.custody import CustodyAssignment, CustodyEvent
from app.models.enums import AuditEventType, ReportType
from app.models.environmental import EnvironmentalEvent
from app.models.exception import ExceptionCase
from app.models.inventory import InventoryTransaction, SampleStorageAssignment, StorageLocation
from app.models.label import SampleLabel
from app.models.lineage import LineageRelationship
from app.models.report import ReportRun
from app.models.sample import Sample, SampleAlias, SampleIdentifier
from app.models.shipment import Shipment
from app.services.audit_service import audit_service
from app.services.lineage_service import lineage_service
from app.services.sample_service import sample_service


class ReportService:
    def sample_history(self, db: Session, sample_uuid: UUID, actor_id: UUID) -> dict:
        sample = sample_service.get_by_uuid(db, sample_uuid)
        shipment = db.get(Shipment, sample.shipment_id) if sample.shipment_id else None
        storage = list(
            db.scalars(
                select(SampleStorageAssignment)
                .options(selectinload(SampleStorageAssignment.storage_location))
                .where(SampleStorageAssignment.sample_id == sample.id)
                .order_by(SampleStorageAssignment.assigned_at)
            )
        )
        moves = list(
            db.scalars(
                select(InventoryTransaction)
                .where(InventoryTransaction.sample_id == sample.id)
                .order_by(InventoryTransaction.created_at)
            )
        )
        custody = list(
            db.scalars(
                select(CustodyAssignment)
                .options(selectinload(CustodyAssignment.custodian))
                .where(CustodyAssignment.sample_id == sample.id)
                .order_by(CustodyAssignment.assigned_at)
            )
        )
        checkout = list(
            db.scalars(
                select(CustodyEvent)
                .where(CustodyEvent.sample_id == sample.id)
                .order_by(CustodyEvent.created_at)
            )
        )
        env = list(
            db.scalars(
                select(EnvironmentalEvent)
                .where(EnvironmentalEvent.sample_id == sample.id)
                .order_by(EnvironmentalEvent.occurred_at)
            )
        )
        exceptions = list(
            db.scalars(
                select(ExceptionCase)
                .where(ExceptionCase.sample_id == sample.id)
                .order_by(ExceptionCase.opened_at)
            )
        )
        labels = list(
            db.scalars(select(SampleLabel).where(SampleLabel.sample_id == sample.id).order_by(SampleLabel.created_at))
        )
        audit = list(
            db.scalars(
                select(AuditEvent)
                .where(AuditEvent.entity_id.in_([str(sample.id), sample.sample_id]))
                .order_by(AuditEvent.timestamp)
            )
        )
        lineage = lineage_service.graph(db, sample.id)
        payload = {
            "identity": sample_service.serialize(sample),
            "shipment": {
                "id": str(shipment.id) if shipment else None,
                "reference": shipment.shipment_reference if shipment else None,
                "status": shipment.status if shipment else None,
            },
            "storage": [
                {
                    "location": a.storage_location.path_label if a.storage_location else None,
                    "assigned_at": a.assigned_at.isoformat(),
                    "ended_at": a.ended_at.isoformat() if a.ended_at else None,
                    "is_active": a.is_active,
                    "reason": a.reason,
                }
                for a in storage
            ],
            "movement": [
                {
                    "type": m.transaction_type,
                    "source_location_id": str(m.source_location_id) if m.source_location_id else None,
                    "destination_location_id": str(m.destination_location_id) if m.destination_location_id else None,
                    "reason": m.reason,
                    "at": m.created_at.isoformat(),
                }
                for m in moves
            ],
            "custody": [
                {
                    "custodian": a.custodian.name if a.custodian else None,
                    "assigned_at": a.assigned_at.isoformat(),
                    "ended_at": a.ended_at.isoformat() if a.ended_at else None,
                    "is_active": a.is_active,
                }
                for a in custody
            ],
            "checkout_events": [
                {
                    "type": e.event_type,
                    "purpose": e.purpose,
                    "checked_out_at": e.checked_out_at.isoformat() if e.checked_out_at else None,
                    "returned_at": e.returned_at.isoformat() if e.returned_at else None,
                    "elapsed_seconds": e.elapsed_seconds,
                    "is_open": e.is_open,
                }
                for e in checkout
            ],
            "lineage": lineage,
            "environmental_events": [
                {
                    "type": e.event_type,
                    "measured_value": str(e.measured_value),
                    "unit": e.unit,
                    "occurred_at": e.occurred_at.isoformat(),
                    "is_excursion": e.is_excursion,
                }
                for e in env
            ],
            "exceptions": [
                {
                    "case_number": c.case_number,
                    "status": c.status,
                    "reason": c.reason,
                    "opened_at": c.opened_at.isoformat(),
                }
                for c in exceptions
            ],
            "labels": [{"label_code": l.label_code, "print_count": l.print_count} for l in labels],
            "audit_timeline": [
                {
                    "event_type": a.event_type,
                    "timestamp": a.timestamp.isoformat(),
                    "reason": a.reason,
                    "after_state": a.after_state,
                }
                for a in audit
            ],
        }
        run = ReportRun(
            report_type=ReportType.SAMPLE_HISTORY.value,
            requested_by=actor_id,
            generated_at=datetime.now(timezone.utc),
            criteria={"sample_id": sample.sample_id},
            row_count=1,
        )
        db.add(run)
        audit_service.record(
            db,
            event_type=AuditEventType.REPORT_GENERATED,
            entity_type="ReportRun",
            entity_id=run.id if run.id else sample.id,
            actor_user_id=actor_id,
            after_state={"report_type": run.report_type, "sample_id": sample.sample_id},
        )
        db.commit()
        payload["report_run_id"] = str(run.id)
        return payload

    def inventory(self, db: Session, actor_id: UUID) -> dict:
        samples = list(
            db.scalars(
                select(Sample)
                .options(
                    selectinload(Sample.current_storage_location),
                    selectinload(Sample.current_custodian),
                    selectinload(Sample.aliases),
                    selectinload(Sample.identifiers),
                )
                .order_by(Sample.sample_id)
            )
        )
        rows = [sample_service.serialize(s) for s in samples]
        run = ReportRun(
            report_type=ReportType.INVENTORY.value,
            requested_by=actor_id,
            generated_at=datetime.now(timezone.utc),
            criteria={},
            row_count=len(rows),
        )
        db.add(run)
        audit_service.record(
            db,
            event_type=AuditEventType.REPORT_GENERATED,
            entity_type="ReportRun",
            entity_id=run.id if run.id else actor_id,
            actor_user_id=actor_id,
            after_state={"report_type": run.report_type, "row_count": len(rows)},
        )
        db.commit()
        return {"report_run_id": str(run.id), "generated_at": run.generated_at.isoformat(), "rows": rows}


report_service = ReportService()


class SearchService:
    def search(self, db: Session, q: str, limit: int = 10) -> list[dict]:
        term = (q or "").strip()
        if len(term) < 2:
            return []
        like = f"%{term}%"
        sample_ids = set()
        for sid in db.scalars(select(Sample.id).where(Sample.sample_id.ilike(like)).limit(limit)):
            sample_ids.add(sid)
        for sid in db.scalars(select(SampleIdentifier.sample_id).where(SampleIdentifier.value.ilike(like)).limit(limit)):
            sample_ids.add(sid)
        for sid in db.scalars(select(SampleAlias.sample_id).where(SampleAlias.value.ilike(like)).limit(limit)):
            sample_ids.add(sid)
        shipments = list(
            db.scalars(select(Shipment).where(Shipment.shipment_reference.ilike(like)).limit(limit))
        )
        results: list[dict] = []
        if sample_ids:
            samples = db.scalars(
                select(Sample)
                .options(selectinload(Sample.aliases), selectinload(Sample.identifiers))
                .where(Sample.id.in_(sample_ids))
            )
            for s in samples:
                results.append(
                    {
                        "kind": "sample",
                        "id": str(s.id),
                        "label": s.sample_id,
                        "subtitle": s.sample_type,
                        "status": s.status,
                    }
                )
        for sh in shipments:
            results.append(
                {
                    "kind": "shipment",
                    "id": str(sh.id),
                    "label": sh.shipment_reference,
                    "subtitle": sh.status,
                    "status": sh.status,
                }
            )
        return results[:limit]


search_service = SearchService()
