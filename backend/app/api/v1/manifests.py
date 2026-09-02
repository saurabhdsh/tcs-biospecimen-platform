from uuid import UUID

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import PlainTextResponse

from app.api.deps import AnyAuthUser, DbSession, OperatorUser
from app.services.manifest_service import manifest_service

router = APIRouter(prefix="/api/v1/manifests", tags=["manifests"])


def _serialize(m):
    return {
        "id": str(m.id),
        "original_filename": m.original_filename,
        "file_type": m.file_type,
        "size_bytes": m.size_bytes,
        "checksum_sha256": m.checksum_sha256,
        "status": m.status,
        "column_mapping": m.column_mapping,
        "uploaded_at": m.uploaded_at.isoformat() if m.uploaded_at else None,
        "validated_at": m.validated_at.isoformat() if m.validated_at else None,
        "committed_at": m.committed_at.isoformat() if m.committed_at else None,
        "row_count": m.row_count,
        "valid_row_count": m.valid_row_count,
        "invalid_row_count": m.invalid_row_count,
        "committed_shipment_id": str(m.committed_shipment_id) if m.committed_shipment_id else None,
        "created_by": str(m.created_by) if m.created_by else None,
    }


@router.post("")
def upload_manifest(user: OperatorUser, db: DbSession, file: UploadFile = File(...)):
    data = file.file.read()
    manifest = manifest_service.upload(
        db,
        actor_id=user.id,
        filename=file.filename or "manifest.csv",
        content_type=file.content_type,
        data=data,
    )
    return _serialize(manifest)


@router.get("")
def list_manifests(user: AnyAuthUser, db: DbSession):
    return [_serialize(m) for m in manifest_service.list(db)]


@router.get("/{manifest_id}")
def get_manifest(manifest_id: UUID, user: AnyAuthUser, db: DbSession):
    m = manifest_service.get(db, manifest_id)
    payload = _serialize(m)
    payload["rows"] = [
        {
            "id": str(r.id),
            "row_number": r.row_number,
            "source_data": r.source_data,
            "canonical_data": r.canonical_data,
            "is_valid": r.is_valid,
            "committed_sample_id": str(r.committed_sample_id) if r.committed_sample_id else None,
            "errors": [
                {"field_name": e.field_name, "code": e.code, "message": e.message}
                for e in r.errors
            ],
        }
        for r in sorted(m.rows, key=lambda x: x.row_number)
    ]
    payload["validation_errors"] = [
        {
            "row_number": e.row_number,
            "field_name": e.field_name,
            "code": e.code,
            "message": e.message,
        }
        for e in m.validation_errors
    ]
    return payload


@router.post("/{manifest_id}/validate")
def validate_manifest(manifest_id: UUID, user: OperatorUser, db: DbSession):
    return _detail(manifest_service.validate(db, manifest_id, user.id))


def _detail(m):
    payload = _serialize(m)
    payload["rows"] = [
        {
            "id": str(r.id),
            "row_number": r.row_number,
            "source_data": r.source_data,
            "canonical_data": r.canonical_data,
            "is_valid": r.is_valid,
            "committed_sample_id": str(r.committed_sample_id) if r.committed_sample_id else None,
            "errors": [
                {"field_name": e.field_name, "code": e.code, "message": e.message}
                for e in r.errors
            ],
        }
        for r in sorted(m.rows, key=lambda x: x.row_number)
    ]
    payload["validation_errors"] = [
        {
            "row_number": e.row_number,
            "field_name": e.field_name,
            "code": e.code,
            "message": e.message,
        }
        for e in m.validation_errors
    ]
    return payload


@router.post("/{manifest_id}/commit")
def commit_manifest(manifest_id: UUID, user: OperatorUser, db: DbSession):
    return _detail(manifest_service.commit(db, manifest_id, user.id))


@router.get("/{manifest_id}/validation-report")
def validation_report(manifest_id: UUID, user: AnyAuthUser, db: DbSession):
    csv_text = manifest_service.validation_csv(db, manifest_id)
    return PlainTextResponse(csv_text, media_type="text/csv")
