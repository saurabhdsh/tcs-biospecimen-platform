from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import AnyAuthUser, DbSession, OperatorUser, ReviewerUser
from app.models.exception import ExceptionCase
from app.models.label import SampleLabel
from app.models.sample import Sample
from app.models.shipment import Shipment
from app.schemas.common import ReprintRequest, ResolveExceptionRequest
from app.services.custody_service import custody_service
from app.services.exception_service import exception_service
from app.services.inventory_service import inventory_service
from app.services.label_service import label_service
from app.storage.local import storage

labels_router = APIRouter(prefix="/api/v1/labels", tags=["labels"])
inventory_router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])
custodians_router = APIRouter(prefix="/api/v1/custodians", tags=["custody"])
exceptions_router = APIRouter(prefix="/api/v1/exceptions", tags=["exceptions"])
shipments_router = APIRouter(prefix="/api/v1/shipments", tags=["shipments"])


@labels_router.post("/{label_id}/reprint")
def reprint(label_id: UUID, payload: ReprintRequest, user: OperatorUser, db: DbSession):
    label = label_service.reprint(db, label_id, user.id, payload.reason)
    return {
        "id": str(label.id),
        "label_code": label.label_code,
        "print_count": label.print_count,
    }


@labels_router.get("/{label_id}/png")
def label_png(label_id: UUID, user: AnyAuthUser, db: DbSession):
    label = db.get(SampleLabel, label_id)
    if label is None:
        raise HTTPException(status_code=404, detail={"code": "LABEL_NOT_FOUND", "message": "Label not found", "details": {}})
    data = storage.read(label.png_storage_key)
    return Response(content=data, media_type="image/png")


@labels_router.get("/{label_id}/pdf")
def label_pdf(label_id: UUID, user: AnyAuthUser, db: DbSession):
    label = db.get(SampleLabel, label_id)
    if label is None or not label.pdf_storage_key:
        raise HTTPException(status_code=404, detail={"code": "LABEL_NOT_FOUND", "message": "Label PDF not found", "details": {}})
    data = storage.read(label.pdf_storage_key)
    return Response(content=data, media_type="application/pdf")


@inventory_router.get("/tree")
def storage_tree(user: AnyAuthUser, db: DbSession, parent_id: UUID | None = None):
    nodes = inventory_service.tree(db, parent_id)
    return [
        {
            "id": str(n.id),
            "code": n.code,
            "name": n.name,
            "location_type": n.location_type,
            "parent_id": str(n.parent_id) if n.parent_id else None,
            "capacity": n.capacity,
            "path_label": n.path_label,
            "has_children": len(n.children) > 0,
        }
        for n in nodes
    ]


@inventory_router.get("/locations/{location_id}/occupancy")
def occupancy(location_id: UUID, user: AnyAuthUser, db: DbSession):
    return inventory_service.occupancy(db, location_id)


@custodians_router.get("")
def list_custodians(user: AnyAuthUser, db: DbSession):
    return [
        {
            "id": str(c.id),
            "code": c.code,
            "name": c.name,
            "email": c.email,
            "department": c.department,
        }
        for c in custody_service.list_custodians(db)
    ]


@exceptions_router.get("")
def list_exceptions(user: AnyAuthUser, db: DbSession, status: str | None = None):
    cases = exception_service.list_cases(db, status)
    return [
        {
            "id": str(c.id),
            "case_number": c.case_number,
            "sample_id": str(c.sample_id),
            "sample_business_id": c.sample.sample_id if c.sample else None,
            "status": c.status,
            "reason": c.reason,
            "opened_at": c.opened_at.isoformat(),
        }
        for c in cases
    ]


@exceptions_router.get("/{exception_id}")
def get_exception(exception_id: UUID, user: AnyAuthUser, db: DbSession):
    c = exception_service.get(db, exception_id)
    return {
        "id": str(c.id),
        "case_number": c.case_number,
        "sample_id": str(c.sample_id),
        "sample_business_id": c.sample.sample_id if c.sample else None,
        "status": c.status,
        "reason": c.reason,
        "opened_at": c.opened_at.isoformat(),
        "resolution": {
            "disposition": c.resolution.disposition,
            "comment": c.resolution.resolution_comment,
            "resolved_at": c.resolution.resolved_at.isoformat(),
        }
        if c.resolution
        else None,
        "history": [
            {
                "from_status": h.from_status,
                "to_status": h.to_status,
                "comment": h.comment,
                "at": h.created_at.isoformat(),
            }
            for h in c.status_history
        ],
    }


@exceptions_router.post("/{exception_id}/resolve")
def resolve_exception(exception_id: UUID, payload: ResolveExceptionRequest, user: ReviewerUser, db: DbSession):
    c = exception_service.resolve(
        db,
        exception_id=exception_id,
        actor=user,
        resolution_comment=payload.resolution_comment,
        disposition=payload.disposition,
    )
    return get_exception(exception_id, user, db)


@shipments_router.get("")
def list_shipments(user: AnyAuthUser, db: DbSession):
    shipments = list(db.scalars(select(Shipment).order_by(Shipment.created_at.desc())))
    result = []
    for s in shipments:
        total = db.scalar(select(func.count(Sample.id)).where(Sample.shipment_id == s.id)) or 0
        accessioned = (
            db.scalar(
                select(func.count(Sample.id)).where(
                    Sample.shipment_id == s.id, Sample.status != "RECEIVED"
                )
            )
            or 0
        )
        result.append(
            {
                "id": str(s.id),
                "shipment_reference": s.shipment_reference,
                "status": s.status,
                "source_location": s.source_location,
                "manifest_id": str(s.manifest_id) if s.manifest_id else None,
                "sample_count": total,
                "accessioned_count": accessioned,
                "created_at": s.created_at.isoformat(),
            }
        )
    return result


@shipments_router.get("/{shipment_id}")
def get_shipment(shipment_id: UUID, user: AnyAuthUser, db: DbSession):
    from app.services.sample_service import sample_service

    shipment = db.scalar(
        select(Shipment).options(selectinload(Shipment.manifest), selectinload(Shipment.samples)).where(Shipment.id == shipment_id)
    )
    if shipment is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("SHIPMENT_NOT_FOUND", "Shipment not found")
    samples = list(
        db.scalars(
            select(Sample)
            .options(
                selectinload(Sample.aliases),
                selectinload(Sample.identifiers),
                selectinload(Sample.current_storage_location),
                selectinload(Sample.current_custodian),
            )
            .where(Sample.shipment_id == shipment_id)
        )
    )
    accessioned = sum(1 for s in samples if s.status != "RECEIVED")
    return {
        "id": str(shipment.id),
        "shipment_reference": shipment.shipment_reference,
        "status": shipment.status,
        "source_location": shipment.source_location,
        "temperature_requirement": shipment.temperature_requirement,
        "manifest_id": str(shipment.manifest_id) if shipment.manifest_id else None,
        "manifest_filename": shipment.manifest.original_filename if shipment.manifest else None,
        "sample_count": len(samples),
        "received_count": sum(1 for s in samples if s.status == "RECEIVED"),
        "accessioned_count": accessioned,
        "samples": [sample_service.serialize(s) for s in samples],
    }
