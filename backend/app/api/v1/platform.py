from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, AnyAuthUser, DbSession
from app.schemas.common import CreateUserRequest
from app.services.admin_user_service import admin_user_service
from app.services.audit_query_service import audit_query_service
from app.services.dashboard_service import dashboard_service
from app.services.report_service import report_service, search_service
from app.services.sample_service import sample_service
from app.services.traceability_service import traceability_service

dashboard_router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])
search_router = APIRouter(prefix="/api/v1/search", tags=["search"])
audit_router = APIRouter(prefix="/api/v1/audit", tags=["audit"])
reports_router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
trace_router = APIRouter(prefix="/api/v1/traceability", tags=["traceability"])
admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@dashboard_router.get("")
def dashboard(user: AnyAuthUser, db: DbSession):
    return dashboard_service.kpis(db)


@search_router.get("")
def search(q: str, user: AnyAuthUser, db: DbSession, limit: int = 10):
    return search_service.search(db, q, limit)


@audit_router.get("")
def list_audit(
    user: AnyAuthUser,
    db: DbSession,
    event_type: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    rows, total = audit_query_service.list_events(
        db, event_type=event_type, entity_type=entity_type, entity_id=entity_id, page=page, page_size=page_size
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "actor_user_id": str(e.actor_user_id) if e.actor_user_id else None,
                "timestamp": e.timestamp.isoformat(),
                "reason": e.reason,
                "before_state": e.before_state,
                "after_state": e.after_state,
                "metadata": e.extra_metadata,
                "correlation_id": e.correlation_id,
            }
            for e in rows
        ],
    }


@reports_router.get("/sample-history/{sample_id}")
def sample_history(sample_id: UUID, user: AnyAuthUser, db: DbSession):
    return report_service.sample_history(db, sample_id, user.id)


@reports_router.get("/inventory")
def inventory_report(user: AnyAuthUser, db: DbSession):
    return report_service.inventory(db, user.id)


@reports_router.get("/sample-history/{sample_id}/csv")
def sample_history_csv(sample_id: UUID, user: AnyAuthUser, db: DbSession):
    import csv
    import io

    from fastapi.responses import PlainTextResponse

    data = report_service.sample_history(db, sample_id, user.id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["section", "field", "value"])
    ident = data["identity"]
    for k, v in ident.items():
        writer.writerow(["identity", k, v])
    for ev in data["audit_timeline"]:
        writer.writerow(["audit", ev["event_type"], ev["timestamp"]])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv")


@trace_router.get("")
def traceability(user: AnyAuthUser, db: DbSession):
    return traceability_service.matrix(db)


@admin_router.get("/users")
def admin_users(user: AdminUser, db: DbSession):
    return admin_user_service.list_users(db)


@admin_router.post("/users")
def create_admin_user(payload: CreateUserRequest, user: AdminUser, db: DbSession):
    return admin_user_service.create_user(
        db,
        actor_id=user.id,
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
        roles=payload.roles,
    )


@admin_router.delete("/users/{user_id}")
def delete_admin_user(user_id: UUID, user: AdminUser, db: DbSession):
    return admin_user_service.delete_user(db, actor_id=user.id, user_id=user_id)
