from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, DomainError, NotFoundError
from app.models.custody import Custodian, CustodyAssignment, CustodyEvent
from app.models.enums import AuditEventType, SampleStatus
from app.models.inventory import InventoryTransaction, SampleStorageAssignment, StorageLocation
from app.services.audit_service import audit_service
from app.services.inventory_service import inventory_service
from app.services.sample_service import sample_service
from app.services.state_machine import lock_sample, state_machine


class CustodyService:
    def list_custodians(self, db: Session) -> list[Custodian]:
        return list(db.scalars(select(Custodian).where(Custodian.is_active.is_(True)).order_by(Custodian.code)))

    def assign(
        self, db: Session, sample_uuid: UUID, custodian_id: UUID, actor_id: UUID, reason: str | None = None
    ):
        sample = lock_sample(db, sample_uuid)
        custodian = db.get(Custodian, custodian_id)
        if custodian is None or not custodian.is_active:
            raise NotFoundError("CUSTODIAN_NOT_FOUND", "Custodian not found")
        now = datetime.now(timezone.utc)
        current = db.scalar(
            select(CustodyAssignment).where(
                CustodyAssignment.sample_id == sample.id, CustodyAssignment.is_active.is_(True)
            )
        )
        if current:
            current.is_active = False
            current.ended_at = now
        db.add(
            CustodyAssignment(
                sample_id=sample.id,
                custodian_id=custodian.id,
                assigned_at=now,
                is_primary=True,
                is_active=True,
                reason=reason,
                created_by=actor_id,
            )
        )
        sample.current_custodian_id = custodian.id
        audit_service.record(
            db,
            event_type=AuditEventType.CUSTODIAN_ASSIGNED,
            entity_type="Sample",
            entity_id=sample.id,
            actor_user_id=actor_id,
            reason=reason,
            after_state={"custodian": custodian.code, "name": custodian.name},
        )
        db.commit()
        return sample_service.get_by_uuid(db, sample.id)

    def history(self, db: Session, sample_uuid: UUID) -> list[CustodyAssignment]:
        return list(
            db.scalars(
                select(CustodyAssignment)
                .options(selectinload(CustodyAssignment.custodian))
                .where(CustodyAssignment.sample_id == sample_uuid)
                .order_by(CustodyAssignment.assigned_at.desc())
            )
        )

    def checkout(self, db: Session, sample_uuid: UUID, actor_id: UUID, purpose: str):
        if not purpose or not purpose.strip():
            raise DomainError("CHECKOUT_PURPOSE_REQUIRED", "Checkout purpose is required.")
        sample = lock_sample(db, sample_uuid)
        if sample.status == SampleStatus.CHECKED_OUT:
            raise ConflictError("ALREADY_CHECKED_OUT", f"Sample {sample.sample_id} is already checked out.")
        if sample.status == SampleStatus.QUARANTINED:
            raise DomainError("SAMPLE_QUARANTINED", "Quarantined samples cannot be checked out.")
        if sample.status != SampleStatus.IN_STORAGE:
            raise DomainError(
                "INVALID_SAMPLE_STATE",
                f"Only IN_STORAGE samples can be checked out. Current status: {sample.status}.",
            )
        open_event = db.scalar(
            select(CustodyEvent).where(CustodyEvent.sample_id == sample.id, CustodyEvent.is_open.is_(True))
        )
        if open_event:
            raise ConflictError("ALREADY_CHECKED_OUT", "An open checkout already exists for this sample.")
        now = datetime.now(timezone.utc)
        previous_location_id = sample.current_storage_location_id
        active = db.scalar(
            select(SampleStorageAssignment).where(
                SampleStorageAssignment.sample_id == sample.id,
                SampleStorageAssignment.is_active.is_(True),
            )
        )
        if active:
            active.is_active = False
            active.ended_at = now
        db.add(
            CustodyEvent(
                sample_id=sample.id,
                event_type="CHECKOUT",
                purpose=purpose.strip(),
                previous_location_id=previous_location_id,
                checked_out_by=actor_id,
                checked_out_at=now,
                is_open=True,
                created_by=actor_id,
            )
        )
        db.add(
            InventoryTransaction(
                sample_id=sample.id,
                transaction_type="CHECKOUT",
                source_location_id=previous_location_id,
                reason=purpose.strip(),
                created_by=actor_id,
            )
        )
        sample.current_storage_location_id = None
        state_machine.transition(sample, SampleStatus.CHECKED_OUT)
        audit_service.record(
            db,
            event_type=AuditEventType.SAMPLE_CHECKED_OUT,
            entity_type="Sample",
            entity_id=sample.id,
            actor_user_id=actor_id,
            reason=purpose.strip(),
            after_state={"status": sample.status, "previous_location_id": str(previous_location_id) if previous_location_id else None},
        )
        db.commit()
        return sample_service.get_by_uuid(db, sample.id)

    def return_sample(self, db: Session, sample_uuid: UUID, location_id: UUID, actor_id: UUID):
        sample = lock_sample(db, sample_uuid)
        if sample.status != SampleStatus.CHECKED_OUT:
            raise DomainError(
                "INVALID_SAMPLE_STATE",
                f"Only CHECKED_OUT samples can be returned. Current status: {sample.status}.",
            )
        location = db.scalar(select(StorageLocation).where(StorageLocation.id == location_id).with_for_update())
        if location is None:
            raise NotFoundError("LOCATION_NOT_FOUND", "Return location not found")
        inventory_service._assert_position_available(db, location)
        now = datetime.now(timezone.utc)
        open_event = db.scalar(
            select(CustodyEvent)
            .where(CustodyEvent.sample_id == sample.id, CustodyEvent.is_open.is_(True))
            .with_for_update()
        )
        elapsed = None
        if open_event:
            open_event.returned_at = now
            open_event.destination_location_id = location.id
            open_event.is_open = False
            if open_event.checked_out_at:
                elapsed = int((now - open_event.checked_out_at).total_seconds())
                open_event.elapsed_seconds = elapsed
        db.add(
            SampleStorageAssignment(
                sample_id=sample.id,
                storage_location_id=location.id,
                assigned_at=now,
                reason="Return to storage",
                is_active=True,
                created_by=actor_id,
            )
        )
        db.add(
            InventoryTransaction(
                sample_id=sample.id,
                transaction_type="RETURN",
                destination_location_id=location.id,
                reason="Return to storage",
                created_by=actor_id,
            )
        )
        sample.current_storage_location_id = location.id
        state_machine.transition(sample, SampleStatus.IN_STORAGE)
        audit_service.record(
            db,
            event_type=AuditEventType.SAMPLE_RETURNED,
            entity_type="Sample",
            entity_id=sample.id,
            actor_user_id=actor_id,
            after_state={
                "status": sample.status,
                "location": location.path_label,
                "elapsed_seconds": elapsed,
            },
        )
        db.commit()
        return sample_service.get_by_uuid(db, sample.id)


custody_service = CustodyService()
