from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


class AuditService:
    def record(
        self,
        db: Session,
        *,
        event_type: str,
        entity_type: str,
        entity_id: UUID | str,
        actor_user_id: UUID | None,
        reason: str | None = None,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_user_id=actor_user_id,
            timestamp=datetime.now(timezone.utc),
            reason=reason,
            before_state=before_state,
            after_state=after_state,
            extra_metadata=metadata,
            correlation_id=correlation_id,
        )
        db.add(event)
        db.flush()
        return event


audit_service = AuditService()
