from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, DomainError, NotFoundError
from app.models.custody import Custodian, CustodyAssignment, CustodyEvent
from app.models.enums import (
    AliasType,
    AuditEventType,
    IdentifierType,
    SampleStatus,
    ShipmentStatus,
)
from app.models.inventory import InventoryTransaction, SampleStorageAssignment, StorageLocation
from app.models.label import LabelPrintEvent, SampleLabel
from app.models.lineage import LineageRelationship, QuantityTransaction
from app.models.sample import Sample, SampleAlias, SampleIdentifier
from app.models.shipment import Shipment, ShipmentSample
from app.services.audit_service import audit_service
from app.services.sample_id_service import sample_id_service
from app.services.state_machine import lock_sample, state_machine


def _serialize_sample(sample: Sample) -> dict[str, Any]:
    barcode = next((a.value for a in sample.aliases if a.alias_type == AliasType.BARCODE), None)
    external_id = next(
        (i.value for i in sample.identifiers if i.identifier_type == IdentifierType.EXTERNAL), None
    )
    location = None
    if sample.current_storage_location:
        location = {
            "id": str(sample.current_storage_location.id),
            "code": sample.current_storage_location.code,
            "path_label": sample.current_storage_location.path_label,
        }
    custodian = None
    if sample.current_custodian:
        custodian = {
            "id": str(sample.current_custodian.id),
            "code": sample.current_custodian.code,
            "name": sample.current_custodian.name,
        }
    return {
        "id": str(sample.id),
        "sample_id": sample.sample_id,
        "status": sample.status,
        "sample_type": sample.sample_type,
        "material_type": sample.material_type,
        "quantity_original": str(sample.quantity_original),
        "quantity_remaining": str(sample.quantity_remaining),
        "quantity_unit": sample.quantity_unit,
        "external_id": external_id,
        "barcode": barcode,
        "collection_date": sample.collection_date.isoformat() if sample.collection_date else None,
        "received_date": sample.received_date.isoformat() if sample.received_date else None,
        "source_location": sample.source_location,
        "temperature_requirement": sample.temperature_requirement,
        "restriction_flag": sample.restriction_flag,
        "shipment_id": str(sample.shipment_id) if sample.shipment_id else None,
        "shipment_reference": sample.shipment.shipment_reference if sample.shipment else None,
        "current_location": location,
        "custodian": custodian,
        "accessioned_at": sample.accessioned_at.isoformat() if sample.accessioned_at else None,
        "created_at": sample.created_at.isoformat() if sample.created_at else None,
    }


class SampleService:
    def create_sample(
        self,
        db: Session,
        *,
        actor_id: UUID,
        sample_type: str,
        quantity: Decimal,
        quantity_unit: str,
        material_type: str | None = None,
        external_id: str | None = None,
        barcode: str | None = None,
        collection_date: date | None = None,
        received_date: date | None = None,
        source_location: str | None = None,
        temperature_requirement: str | None = None,
        shipment_id: UUID | None = None,
        status: SampleStatus = SampleStatus.RECEIVED,
    ) -> Sample:
        if barcode:
            existing_alias = db.scalar(
                select(SampleAlias).where(
                    SampleAlias.alias_type == AliasType.BARCODE, SampleAlias.value == barcode
                )
            )
            if existing_alias:
                raise ConflictError("DUPLICATE_BARCODE", f"Barcode {barcode} already exists.")
        if external_id:
            existing_ext = db.scalar(
                select(SampleIdentifier).where(
                    SampleIdentifier.identifier_type == IdentifierType.EXTERNAL,
                    SampleIdentifier.value == external_id,
                )
            )
            if existing_ext:
                raise ConflictError(
                    "DUPLICATE_EXTERNAL_ID", f"External sample ID {external_id} already exists."
                )

        internal_id = sample_id_service.next_id(db)
        sample = Sample(
            sample_id=internal_id,
            status=status.value,
            sample_type=sample_type,
            material_type=material_type,
            quantity_original=quantity,
            quantity_remaining=quantity,
            quantity_unit=quantity_unit,
            collection_date=collection_date,
            received_date=received_date,
            source_location=source_location,
            temperature_requirement=temperature_requirement,
            shipment_id=shipment_id,
            created_by=actor_id,
        )
        db.add(sample)
        db.flush()
        db.add(
            SampleIdentifier(
                sample_id=sample.id, identifier_type=IdentifierType.INTERNAL, value=internal_id
            )
        )
        if external_id:
            db.add(
                SampleIdentifier(
                    sample_id=sample.id, identifier_type=IdentifierType.EXTERNAL, value=external_id
                )
            )
        if barcode:
            db.add(SampleAlias(sample_id=sample.id, alias_type=AliasType.BARCODE, value=barcode))
        audit_service.record(
            db,
            event_type=AuditEventType.SAMPLE_CREATED,
            entity_type="Sample",
            entity_id=sample.id,
            actor_user_id=actor_id,
            after_state={"sample_id": internal_id, "barcode": barcode, "external_id": external_id},
        )
        return sample

    def get_by_uuid(self, db: Session, sample_uuid: UUID) -> Sample:
        sample = db.scalar(
            select(Sample)
            .options(
                selectinload(Sample.identifiers),
                selectinload(Sample.aliases),
                selectinload(Sample.shipment),
                selectinload(Sample.current_storage_location),
                selectinload(Sample.current_custodian),
                selectinload(Sample.labels),
            )
            .where(Sample.id == sample_uuid)
        )
        if sample is None:
            raise NotFoundError("SAMPLE_NOT_FOUND", "Sample not found")
        return sample

    def get_by_business_id(self, db: Session, sample_id: str) -> Sample:
        sample = db.scalar(select(Sample).where(Sample.sample_id == sample_id))
        if sample is None:
            raise NotFoundError("SAMPLE_NOT_FOUND", f"Sample {sample_id} not found")
        return self.get_by_uuid(db, sample.id)

    def resolve_lookup(self, db: Session, query: str) -> Sample:
        q = query.strip()
        sample = db.scalar(select(Sample).where(Sample.sample_id == q))
        if sample:
            return self.get_by_uuid(db, sample.id)
        ident = db.scalar(select(SampleIdentifier).where(SampleIdentifier.value == q))
        if ident:
            return self.get_by_uuid(db, ident.sample_id)
        alias = db.scalar(select(SampleAlias).where(SampleAlias.value == q))
        if alias:
            return self.get_by_uuid(db, alias.sample_id)
        raise NotFoundError("SAMPLE_NOT_FOUND", f"No sample matches '{q}'")

    def list_samples(
        self,
        db: Session,
        *,
        sample_id: str | None = None,
        barcode: str | None = None,
        sample_type: str | None = None,
        status: str | None = None,
        site: str | None = None,
        freezer: str | None = None,
        rack: str | None = None,
        box: str | None = None,
        custodian: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Sample], int]:
        stmt = select(Sample).options(
            selectinload(Sample.identifiers),
            selectinload(Sample.aliases),
            selectinload(Sample.shipment),
            selectinload(Sample.current_storage_location),
            selectinload(Sample.current_custodian),
        )
        count_stmt = select(func.count(Sample.id))
        filters = []
        if sample_id:
            filters.append(
                or_(
                    Sample.sample_id.ilike(f"%{sample_id}%"),
                    Sample.id.in_(
                        select(SampleIdentifier.sample_id).where(
                            SampleIdentifier.value.ilike(f"%{sample_id}%")
                        )
                    ),
                )
            )
        if barcode:
            filters.append(
                Sample.id.in_(
                    select(SampleAlias.sample_id).where(
                        SampleAlias.alias_type == AliasType.BARCODE,
                        SampleAlias.value.ilike(f"%{barcode}%"),
                    )
                )
            )
        if sample_type:
            filters.append(Sample.sample_type.ilike(f"%{sample_type}%"))
        if status:
            filters.append(Sample.status == status)
        if custodian:
            filters.append(
                Sample.current_custodian_id.in_(
                    select(Custodian.id).where(
                        or_(Custodian.code.ilike(f"%{custodian}%"), Custodian.name.ilike(f"%{custodian}%"))
                    )
                )
            )
        if any([site, freezer, rack, box]):
            loc_stmt = select(StorageLocation.id)
            loc_filters = []
            if box:
                loc_filters.append(
                    or_(StorageLocation.code.ilike(f"%{box}%"), StorageLocation.path_label.ilike(f"%{box}%"))
                )
            if freezer:
                loc_filters.append(StorageLocation.path_label.ilike(f"%{freezer}%"))
            if rack:
                loc_filters.append(StorageLocation.path_label.ilike(f"%{rack}%"))
            if site:
                loc_filters.append(StorageLocation.path_label.ilike(f"%{site}%"))
            loc_ids = loc_stmt.where(and_(*loc_filters)) if loc_filters else loc_stmt
            filters.append(Sample.current_storage_location_id.in_(loc_ids))
        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))
        total = db.scalar(count_stmt) or 0
        rows = list(
            db.scalars(stmt.order_by(Sample.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
        )
        return rows, total

    def accession(self, db: Session, sample_uuid: UUID, actor_id: UUID) -> Sample:
        sample = lock_sample(db, sample_uuid)
        if sample.status != SampleStatus.RECEIVED:
            raise DomainError(
                "ALREADY_ACCESSIONED",
                f"Sample {sample.sample_id} cannot be accessioned from status {sample.status}.",
                details={"status": sample.status},
            )
        before = {"status": sample.status}
        state_machine.transition(sample, SampleStatus.ACCESSIONED)
        sample.accessioned_at = datetime.now(timezone.utc)
        sample.accessioned_by = actor_id
        if sample.shipment_id:
            shipment = db.get(Shipment, sample.shipment_id)
            if shipment:
                shipment.status = ShipmentStatus.ACCESSIONING.value
        audit_service.record(
            db,
            event_type=AuditEventType.SAMPLE_ACCESSIONED,
            entity_type="Sample",
            entity_id=sample.id,
            actor_user_id=actor_id,
            before_state=before,
            after_state={"status": sample.status, "accessioned_at": sample.accessioned_at.isoformat()},
        )
        db.commit()
        db.refresh(sample)
        return self.get_by_uuid(db, sample.id)

    def serialize(self, sample: Sample) -> dict[str, Any]:
        return _serialize_sample(sample)


sample_service = SampleService()
