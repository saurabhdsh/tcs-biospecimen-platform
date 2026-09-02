from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.exception import ExceptionCase
from app.models.sample import Sample
from app.models.shipment import Shipment
from app.services.inventory_service import inventory_service


class DashboardService:
    def kpis(self, db: Session) -> dict:
        def count_status(status: str) -> int:
            return db.scalar(select(func.count(Sample.id)).where(Sample.status == status)) or 0

        total = db.scalar(select(func.count(Sample.id))) or 0
        open_exceptions = (
            db.scalar(
                select(func.count(ExceptionCase.id)).where(ExceptionCase.status.in_(["OPEN", "UNDER_REVIEW"]))
            )
            or 0
        )
        shipments = db.scalar(select(func.count(Shipment.id))) or 0
        by_status_rows = db.execute(select(Sample.status, func.count(Sample.id)).group_by(Sample.status)).all()
        occupancy = inventory_service.occupancy_summary(db)
        recent = list(
            db.scalars(select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(15))
        )
        return {
            "total_samples": total,
            "received": count_status("RECEIVED"),
            "accessioned": count_status("ACCESSIONED")
            + count_status("IN_STORAGE")
            + count_status("CHECKED_OUT")
            + count_status("QUARANTINED")
            + count_status("RELEASED")
            + count_status("DISPOSED"),
            "in_storage": count_status("IN_STORAGE"),
            "checked_out": count_status("CHECKED_OUT"),
            "quarantined": count_status("QUARANTINED"),
            "open_exceptions": open_exceptions,
            "shipments": shipments,
            "samples_by_status": [{"status": s, "count": c} for s, c in by_status_rows],
            "storage_occupancy": occupancy,
            "recent_activity": [
                {
                    "id": str(e.id),
                    "event_type": e.event_type,
                    "entity_type": e.entity_type,
                    "entity_id": e.entity_id,
                    "timestamp": e.timestamp.isoformat(),
                    "reason": e.reason,
                }
                for e in recent
            ],
        }


dashboard_service = DashboardService()
