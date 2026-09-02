from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, DomainError, NotFoundError
from app.models.enums import AuditEventType, SampleStatus, StorageLocationType
from app.models.inventory import InventoryTransaction, SampleStorageAssignment, StorageLocation
from app.models.sample import Sample
from app.services.audit_service import audit_service
from app.services.sample_service import sample_service
from app.services.state_machine import lock_sample, state_machine


class InventoryService:
    def get_location(self, db: Session, location_id: UUID) -> StorageLocation:
        loc = db.get(StorageLocation, location_id)
        if loc is None:
            raise NotFoundError("LOCATION_NOT_FOUND", "Storage location not found")
        return loc

    def tree(self, db: Session, parent_id: UUID | None = None) -> list[StorageLocation]:
        stmt = select(StorageLocation).options(selectinload(StorageLocation.children))
        if parent_id is None:
            stmt = stmt.where(StorageLocation.parent_id.is_(None))
        else:
            stmt = stmt.where(StorageLocation.parent_id == parent_id)
        return list(db.scalars(stmt.order_by(StorageLocation.code)))

    def occupancy(self, db: Session, location_id: UUID) -> dict:
        loc = self.get_location(db, location_id)
        active = list(
            db.scalars(
                select(SampleStorageAssignment)
                .options(selectinload(SampleStorageAssignment.sample))
                .where(
                    SampleStorageAssignment.storage_location_id == location_id,
                    SampleStorageAssignment.is_active.is_(True),
                )
            )
        )
        occupied = len(active)
        sample = active[0].sample if active else None
        status = "available"
        if occupied >= loc.capacity:
            status = "occupied"
        if sample and sample.status == SampleStatus.QUARANTINED:
            status = "quarantined"
        return {
            "location_id": str(loc.id),
            "code": loc.code,
            "path_label": loc.path_label,
            "location_type": loc.location_type,
            "capacity": loc.capacity,
            "occupied": occupied,
            "available": max(loc.capacity - occupied, 0),
            "status": status,
            "sample": sample_service.serialize(sample) if sample else None,
        }

    def _assert_position_available(self, db: Session, location: StorageLocation) -> None:
        if location.location_type != StorageLocationType.POSITION:
            raise DomainError("INVALID_STORAGE_TARGET", "Samples can only be assigned to POSITION locations.")
        count = db.scalar(
            select(func.count(SampleStorageAssignment.id)).where(
                SampleStorageAssignment.storage_location_id == location.id,
                SampleStorageAssignment.is_active.is_(True),
            )
        ) or 0
        if count >= location.capacity:
            raise ConflictError(
                "POSITION_OCCUPIED",
                f"Position {location.path_label} is already occupied.",
                details={"capacity": location.capacity, "occupied": count},
            )

    def _close_active_assignment(self, db: Session, sample: Sample, now: datetime) -> UUID | None:
        current = db.scalar(
            select(SampleStorageAssignment).where(
                SampleStorageAssignment.sample_id == sample.id,
                SampleStorageAssignment.is_active.is_(True),
            )
        )
        source_id = sample.current_storage_location_id
        if current:
            current.is_active = False
            current.ended_at = now
            source_id = current.storage_location_id
        return source_id

    def assign(
        self, db: Session, sample_uuid: UUID, location_id: UUID, actor_id: UUID, reason: str | None = None
    ) -> Sample:
        sample = lock_sample(db, sample_uuid)
        location = db.scalar(select(StorageLocation).where(StorageLocation.id == location_id).with_for_update())
        if location is None:
            raise NotFoundError("LOCATION_NOT_FOUND", "Storage location not found")
        if sample.status == SampleStatus.QUARANTINED:
            raise DomainError("SAMPLE_QUARANTINED", "Quarantined samples cannot be moved.")
        if sample.status not in {SampleStatus.ACCESSIONED, SampleStatus.IN_STORAGE}:
            raise DomainError(
                "INVALID_SAMPLE_STATE",
                f"Sample {sample.sample_id} in status {sample.status} cannot be assigned storage.",
            )
        self._assert_position_available(db, location)
        now = datetime.now(timezone.utc)
        before = {"status": sample.status, "location_id": str(sample.current_storage_location_id) if sample.current_storage_location_id else None}
        source_id = self._close_active_assignment(db, sample, now)
        db.add(
            SampleStorageAssignment(
                sample_id=sample.id,
                storage_location_id=location.id,
                assigned_at=now,
                reason=reason,
                is_active=True,
                created_by=actor_id,
            )
        )
        db.add(
            InventoryTransaction(
                sample_id=sample.id,
                transaction_type="ASSIGN",
                source_location_id=source_id,
                destination_location_id=location.id,
                reason=reason,
                created_by=actor_id,
            )
        )
        sample.current_storage_location_id = location.id
        if sample.status == SampleStatus.ACCESSIONED:
            state_machine.transition(sample, SampleStatus.IN_STORAGE)
        audit_service.record(
            db,
            event_type=AuditEventType.STORAGE_ASSIGNED,
            entity_type="Sample",
            entity_id=sample.id,
            actor_user_id=actor_id,
            reason=reason,
            before_state=before,
            after_state={"status": sample.status, "location": location.path_label},
        )
        db.commit()
        return sample_service.get_by_uuid(db, sample.id)

    def move(
        self, db: Session, sample_uuid: UUID, destination_id: UUID, actor_id: UUID, reason: str
    ) -> Sample:
        if not reason or not reason.strip():
            raise DomainError("MOVE_REASON_REQUIRED", "A reason is required to move a sample.")
        sample = lock_sample(db, sample_uuid)
        if sample.status == SampleStatus.QUARANTINED:
            raise DomainError("SAMPLE_QUARANTINED", "Quarantined samples cannot be moved.")
        if sample.status != SampleStatus.IN_STORAGE:
            raise DomainError(
                "INVALID_SAMPLE_STATE",
                f"Only IN_STORAGE samples can be moved. Current status: {sample.status}.",
            )
        destination = db.scalar(select(StorageLocation).where(StorageLocation.id == destination_id).with_for_update())
        if destination is None:
            raise NotFoundError("LOCATION_NOT_FOUND", "Destination location not found")
        self._assert_position_available(db, destination)
        now = datetime.now(timezone.utc)
        source_id = self._close_active_assignment(db, sample, now)
        db.add(
            SampleStorageAssignment(
                sample_id=sample.id,
                storage_location_id=destination.id,
                assigned_at=now,
                reason=reason.strip(),
                is_active=True,
                created_by=actor_id,
            )
        )
        db.add(
            InventoryTransaction(
                sample_id=sample.id,
                transaction_type="MOVE",
                source_location_id=source_id,
                destination_location_id=destination.id,
                reason=reason.strip(),
                created_by=actor_id,
            )
        )
        sample.current_storage_location_id = destination.id
        audit_service.record(
            db,
            event_type=AuditEventType.SAMPLE_MOVED,
            entity_type="Sample",
            entity_id=sample.id,
            actor_user_id=actor_id,
            reason=reason.strip(),
            before_state={"location_id": str(source_id) if source_id else None},
            after_state={"location": destination.path_label},
        )
        db.commit()
        return sample_service.get_by_uuid(db, sample.id)

    def occupancy_summary(self, db: Session) -> dict:
        positions = list(
            db.scalars(select(StorageLocation).where(StorageLocation.location_type == StorageLocationType.POSITION))
        )
        occupied_ids = set(
            db.scalars(
                select(SampleStorageAssignment.storage_location_id).where(
                    SampleStorageAssignment.is_active.is_(True)
                )
            )
        )
        total = len(positions)
        occupied = sum(1 for p in positions if p.id in occupied_ids)
        return {"total_positions": total, "occupied": occupied, "available": total - occupied}


inventory_service = InventoryService()
