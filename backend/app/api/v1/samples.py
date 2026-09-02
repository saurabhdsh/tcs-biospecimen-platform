from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.api.deps import AnyAuthUser, DbSession, OperatorUser
from app.schemas.common import (
    CheckoutRequest,
    ChildSampleRequest,
    CustodianAssignRequest,
    EnvironmentalEventRequest,
    MoveRequest,
    ReturnRequest,
    StorageAssignRequest,
)
from app.services.custody_service import custody_service
from app.services.environmental_service import environmental_service
from app.services.inventory_service import inventory_service
from app.services.label_service import label_service
from app.services.lineage_service import lineage_service
from app.services.sample360_service import sample360_service
from app.services.sample_service import sample_service

router = APIRouter(prefix="/api/v1/samples", tags=["samples"])


@router.get("")
def list_samples(
    user: AnyAuthUser,
    db: DbSession,
    sample_id: str | None = None,
    barcode: str | None = None,
    sample_type: str | None = None,
    status: str | None = None,
    site: str | None = None,
    freezer: str | None = None,
    rack: str | None = None,
    box: str | None = None,
    custodian: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
):
    rows, total = sample_service.list_samples(
        db,
        sample_id=sample_id,
        barcode=barcode,
        sample_type=sample_type,
        status=status,
        site=site,
        freezer=freezer,
        rack=rack,
        box=box,
        custodian=custodian,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [sample_service.serialize(s) for s in rows],
    }


@router.get("/lookup")
def lookup_sample(q: str, user: AnyAuthUser, db: DbSession):
    sample = sample_service.resolve_lookup(db, q)
    return sample_service.serialize(sample)


@router.get("/{sample_id}")
def get_sample(sample_id: UUID, user: AnyAuthUser, db: DbSession):
    return sample_service.serialize(sample_service.get_by_uuid(db, sample_id))


@router.get("/{sample_id}/360")
def sample_360(sample_id: UUID, user: AnyAuthUser, db: DbSession):
    return sample360_service.build(db, sample_id)


@router.post("/{sample_id}/accession")
def accession(sample_id: UUID, user: OperatorUser, db: DbSession):
    return sample_service.serialize(sample_service.accession(db, sample_id, user.id))


@router.post("/{sample_id}/labels")
def create_label(sample_id: UUID, user: OperatorUser, db: DbSession):
    label = label_service.generate(db, sample_id, user.id)
    return {
        "id": str(label.id),
        "label_code": label.label_code,
        "print_count": label.print_count,
        "png_url": f"/api/v1/labels/{label.id}/png",
        "pdf_url": f"/api/v1/labels/{label.id}/pdf",
    }


@router.post("/{sample_id}/storage")
def assign_storage(sample_id: UUID, payload: StorageAssignRequest, user: OperatorUser, db: DbSession):
    return sample_service.serialize(
        inventory_service.assign(db, sample_id, payload.storage_location_id, user.id, payload.reason)
    )


@router.post("/{sample_id}/move")
def move_sample(sample_id: UUID, payload: MoveRequest, user: OperatorUser, db: DbSession):
    return sample_service.serialize(
        inventory_service.move(db, sample_id, payload.destination_location_id, user.id, payload.reason)
    )


@router.post("/{sample_id}/custodian")
def assign_custodian(sample_id: UUID, payload: CustodianAssignRequest, user: OperatorUser, db: DbSession):
    return sample_service.serialize(
        custody_service.assign(db, sample_id, payload.custodian_id, user.id, payload.reason)
    )


@router.get("/{sample_id}/custodian")
def custodian_history(sample_id: UUID, user: AnyAuthUser, db: DbSession):
    rows = custody_service.history(db, sample_id)
    return [
        {
            "id": str(a.id),
            "custodian_id": str(a.custodian_id),
            "custodian": a.custodian.name if a.custodian else None,
            "code": a.custodian.code if a.custodian else None,
            "assigned_at": a.assigned_at.isoformat(),
            "ended_at": a.ended_at.isoformat() if a.ended_at else None,
            "is_active": a.is_active,
            "reason": a.reason,
        }
        for a in rows
    ]


@router.post("/{sample_id}/checkout")
def checkout(sample_id: UUID, payload: CheckoutRequest, user: OperatorUser, db: DbSession):
    return sample_service.serialize(custody_service.checkout(db, sample_id, user.id, payload.purpose))


@router.post("/{sample_id}/return")
def return_sample(sample_id: UUID, payload: ReturnRequest, user: OperatorUser, db: DbSession):
    return sample_service.serialize(
        custody_service.return_sample(db, sample_id, payload.storage_location_id, user.id)
    )


@router.post("/{parent_id}/children")
def create_child(parent_id: UUID, payload: ChildSampleRequest, user: OperatorUser, db: DbSession):
    child = lineage_service.create_child(
        db,
        parent_id=parent_id,
        actor_id=user.id,
        relationship_type=payload.relationship_type,
        output_quantity=payload.output_quantity,
        output_unit=payload.output_unit,
        parent_quantity_consumed=payload.parent_quantity_consumed,
        child_sample_type=payload.child_sample_type,
        existing_child_id=payload.existing_child_id,
    )
    return sample_service.serialize(child)


@router.get("/{sample_id}/lineage")
def get_lineage(sample_id: UUID, user: AnyAuthUser, db: DbSession):
    return lineage_service.graph(db, sample_id)


@router.post("/{sample_id}/environmental-events")
def record_environmental(
    sample_id: UUID,
    user: OperatorUser,
    db: DbSession,
    measured_value: str = Form(...),
    unit: str = Form("C"),
    acceptable_min: str = Form(...),
    acceptable_max: str = Form(...),
    occurred_at: str | None = Form(None),
    source: str | None = Form(None),
    notes: str | None = Form(None),
    create_exception: bool = Form(True),
    evidence: UploadFile | None = File(None),
):
    from decimal import Decimal

    occurred = datetime.fromisoformat(occurred_at) if occurred_at else datetime.now(timezone.utc)
    evidence_bytes = evidence.file.read() if evidence else None
    event = environmental_service.record_event(
        db,
        sample_uuid=sample_id,
        actor_id=user.id,
        measured_value=Decimal(measured_value),
        unit=unit,
        acceptable_min=Decimal(acceptable_min),
        acceptable_max=Decimal(acceptable_max),
        occurred_at=occurred,
        source=source,
        notes=notes,
        evidence_filename=evidence.filename if evidence else None,
        evidence_content_type=evidence.content_type if evidence else None,
        evidence_bytes=evidence_bytes,
        create_exception=create_exception,
    )
    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "measured_value": str(event.measured_value),
        "is_excursion": event.is_excursion,
        "sample_id": str(event.sample_id),
    }


@router.post("/{sample_id}/environmental-events/json")
def record_environmental_json(
    sample_id: UUID, payload: EnvironmentalEventRequest, user: OperatorUser, db: DbSession
):
    event = environmental_service.record_event(
        db,
        sample_uuid=sample_id,
        actor_id=user.id,
        measured_value=payload.measured_value,
        unit=payload.unit,
        acceptable_min=payload.acceptable_min,
        acceptable_max=payload.acceptable_max,
        occurred_at=payload.occurred_at or datetime.now(timezone.utc),
        source=payload.source,
        notes=payload.notes,
        create_exception=payload.create_exception,
    )
    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "measured_value": str(event.measured_value),
        "is_excursion": event.is_excursion,
        "sample_id": str(event.sample_id),
    }
