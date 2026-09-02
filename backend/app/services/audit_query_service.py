from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.audit import AuditEvent
from app.models.user import User


class AuditQueryService:
    def list_events(
        self,
        db: Session,
        *,
        event_type: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditEvent], int]:
        from sqlalchemy import func

        stmt = select(AuditEvent)
        count_stmt = select(func.count(AuditEvent.id))
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
            count_stmt = count_stmt.where(AuditEvent.event_type == event_type)
        if entity_type:
            stmt = stmt.where(AuditEvent.entity_type == entity_type)
            count_stmt = count_stmt.where(AuditEvent.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AuditEvent.entity_id == entity_id)
            count_stmt = count_stmt.where(AuditEvent.entity_id == entity_id)
        total = db.scalar(count_stmt) or 0
        rows = list(
            db.scalars(
                stmt.order_by(AuditEvent.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
            )
        )
        return rows, total


audit_query_service = AuditQueryService()
