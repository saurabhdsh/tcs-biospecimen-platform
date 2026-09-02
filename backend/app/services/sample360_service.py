from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.audit import AuditEvent
from app.models.custody import CustodyAssignment, CustodyEvent
from app.models.environmental import EnvironmentalEvent
from app.models.exception import ExceptionCase
from app.models.inventory import InventoryTransaction
from app.models.label import SampleLabel
from app.models.user import User
from app.services.lineage_service import lineage_service
from app.services.sample_service import sample_service


class Sample360Service:
    def build(self, db: Session, sample_uuid) -> dict:
        sample = sample_service.get_by_uuid(db, sample_uuid)
        identity = sample_service.serialize(sample)
        audit = list(
            db.scalars(
                select(AuditEvent)
                .where(AuditEvent.entity_id.in_([str(sample.id), sample.sample_id]))
                .order_by(AuditEvent.timestamp.desc())
            )
        )
        labels = list(
            db.scalars(
                select(SampleLabel)
                .options(selectinload(SampleLabel.print_events))
                .where(SampleLabel.sample_id == sample.id)
                .order_by(SampleLabel.created_at.desc())
            )
        )
        env = list(
            db.scalars(
                select(EnvironmentalEvent)
                .where(EnvironmentalEvent.sample_id == sample.id)
                .order_by(EnvironmentalEvent.occurred_at.desc())
            )
        )
        exceptions = list(
            db.scalars(
                select(ExceptionCase)
                .options(selectinload(ExceptionCase.resolution))
                .where(ExceptionCase.sample_id == sample.id)
                .order_by(ExceptionCase.opened_at.desc())
            )
        )
        custody = list(
            db.scalars(
                select(CustodyAssignment)
                .options(selectinload(CustodyAssignment.custodian))
                .where(CustodyAssignment.sample_id == sample.id)
                .order_by(CustodyAssignment.assigned_at.desc())
            )
        )
        events = list(
            db.scalars(
                select(CustodyEvent)
                .where(CustodyEvent.sample_id == sample.id)
                .order_by(CustodyEvent.created_at.desc())
            )
        )
        moves = list(
            db.scalars(
                select(InventoryTransaction)
                .where(InventoryTransaction.sample_id == sample.id)
                .order_by(InventoryTransaction.created_at.desc())
            )
        )
        return {
            "overview": identity,
            "identity": {
                "internal_id": sample.sample_id,
                "identifiers": [
                    {"type": i.identifier_type, "value": i.value} for i in sample.identifiers
                ],
                "aliases": [{"type": a.alias_type, "value": a.value} for a in sample.aliases],
            },
            "shipment": {
                "id": str(sample.shipment.id) if sample.shipment else None,
                "reference": sample.shipment.shipment_reference if sample.shipment else None,
                "status": sample.shipment.status if sample.shipment else None,
            },
            "inventory": [
                {
                    "type": m.transaction_type,
                    "reason": m.reason,
                    "at": m.created_at.isoformat(),
                    "source_location_id": str(m.source_location_id) if m.source_location_id else None,
                    "destination_location_id": str(m.destination_location_id) if m.destination_location_id else None,
                }
                for m in moves
            ],
            "custody": {
                "assignments": [
                    {
                        "custodian": a.custodian.name if a.custodian else None,
                        "code": a.custodian.code if a.custodian else None,
                        "assigned_at": a.assigned_at.isoformat(),
                        "ended_at": a.ended_at.isoformat() if a.ended_at else None,
                        "is_active": a.is_active,
                    }
                    for a in custody
                ],
                "events": [
                    {
                        "type": e.event_type,
                        "purpose": e.purpose,
                        "checked_out_at": e.checked_out_at.isoformat() if e.checked_out_at else None,
                        "returned_at": e.returned_at.isoformat() if e.returned_at else None,
                        "elapsed_seconds": e.elapsed_seconds,
                        "is_open": e.is_open,
                    }
                    for e in events
                ],
            },
            "lineage": lineage_service.graph(db, sample.id),
            "environmental": [
                {
                    "id": str(e.id),
                    "type": e.event_type,
                    "measured_value": str(e.measured_value),
                    "unit": e.unit,
                    "acceptable_min": str(e.acceptable_min),
                    "acceptable_max": str(e.acceptable_max),
                    "occurred_at": e.occurred_at.isoformat(),
                    "source": e.source,
                    "notes": e.notes,
                    "is_excursion": e.is_excursion,
                }
                for e in env
            ],
            "exceptions": [
                {
                    "id": str(c.id),
                    "case_number": c.case_number,
                    "status": c.status,
                    "reason": c.reason,
                    "opened_at": c.opened_at.isoformat(),
                    "disposition": c.resolution.disposition if c.resolution else None,
                }
                for c in exceptions
            ],
            "labels": [
                {
                    "id": str(lbl.id),
                    "label_code": lbl.label_code,
                    "print_count": lbl.print_count,
                    "png_url": f"/api/v1/labels/{lbl.id}/png",
                    "pdf_url": f"/api/v1/labels/{lbl.id}/pdf",
                    "print_events": [
                        {
                            "sequence_number": pe.sequence_number,
                            "reason": pe.reason,
                            "is_reprint": pe.is_reprint,
                            "at": pe.created_at.isoformat(),
                        }
                        for pe in lbl.print_events
                    ],
                }
                for lbl in labels
            ],
            "audit": [
                {
                    "id": str(a.id),
                    "event_type": a.event_type,
                    "timestamp": a.timestamp.isoformat(),
                    "reason": a.reason,
                    "before_state": a.before_state,
                    "after_state": a.after_state,
                }
                for a in audit
            ],
        }


sample360_service = Sample360Service()
