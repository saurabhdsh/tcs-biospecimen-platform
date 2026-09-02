from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
import hashlib

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models.enums import AuditEventType, EnvironmentalEventType
from app.models.environmental import EnvironmentalEvent, EvidenceAttachment
from app.services.audit_service import audit_service
from app.services.exception_service import exception_service
from app.services.sample_service import sample_service
from app.storage.local import storage


class EnvironmentalService:
    def record_event(
        self,
        db: Session,
        *,
        sample_uuid: UUID,
        actor_id: UUID,
        measured_value: Decimal,
        unit: str,
        acceptable_min: Decimal,
        acceptable_max: Decimal,
        occurred_at: datetime,
        source: str | None,
        notes: str | None,
        evidence_filename: str | None = None,
        evidence_content_type: str | None = None,
        evidence_bytes: bytes | None = None,
        create_exception: bool = True,
    ) -> EnvironmentalEvent:
        sample = sample_service.get_by_uuid(db, sample_uuid)
        is_excursion = measured_value < acceptable_min or measured_value > acceptable_max
        event = EnvironmentalEvent(
            sample_id=sample.id,
            event_type=EnvironmentalEventType.TEMPERATURE_EXCURSION.value,
            measured_value=measured_value,
            unit=unit,
            acceptable_min=acceptable_min,
            acceptable_max=acceptable_max,
            occurred_at=occurred_at,
            source=source,
            notes=notes,
            is_excursion=is_excursion,
            created_by=actor_id,
        )
        db.add(event)
        db.flush()
        if evidence_bytes and evidence_filename:
            key = f"evidence/{event.id}/{uuid4()}-{evidence_filename}"
            storage.save(key, evidence_bytes)
            db.add(
                EvidenceAttachment(
                    environmental_event_id=event.id,
                    filename=evidence_filename,
                    content_type=evidence_content_type,
                    size_bytes=len(evidence_bytes),
                    storage_key=key,
                    checksum_sha256=hashlib.sha256(evidence_bytes).hexdigest(),
                    created_by=actor_id,
                )
            )
        audit_service.record(
            db,
            event_type=AuditEventType.TEMPERATURE_EXCURSION_RECORDED,
            entity_type="EnvironmentalEvent",
            entity_id=event.id,
            actor_user_id=actor_id,
            after_state={
                "sample_id": sample.sample_id,
                "measured_value": str(measured_value),
                "unit": unit,
                "is_excursion": is_excursion,
            },
        )
        db.flush()
        if is_excursion and create_exception:
            exception_service.create_from_event(db, event=event, actor_id=actor_id, commit=False)
        db.commit()
        db.refresh(event)
        return event


environmental_service = EnvironmentalService()
