from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.manifests import router as manifests_router
from app.api.v1.ops import (
    custodians_router,
    exceptions_router,
    inventory_router,
    labels_router,
    shipments_router,
)
from app.api.v1.platform import (
    admin_router,
    audit_router,
    dashboard_router,
    reports_router,
    search_router,
    trace_router,
)
from app.api.v1.samples import router as samples_router
from app.core.config import settings
from app.core.errors import DomainError
from app.core.logging import configure_logging
from app.core.middleware import CorrelationIdMiddleware
from app.models import load_all_models

configure_logging()
load_all_models()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Biospecimen intake, inventory, lineage, and exception management platform.",
)


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(manifests_router)
app.include_router(samples_router)
app.include_router(labels_router)
app.include_router(inventory_router)
app.include_router(custodians_router)
app.include_router(exceptions_router)
app.include_router(shipments_router)
app.include_router(dashboard_router)
app.include_router(search_router)
app.include_router(audit_router)
app.include_router(reports_router)
app.include_router(trace_router)
app.include_router(admin_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    from sqlalchemy import text

    from app.db.session import engine

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ready"}
