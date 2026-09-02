from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import LoginRequest
from app.services.auth_service import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, db: DbSession):
    user, token = auth_service.authenticate(db, payload.email.strip().lower(), payload.password)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "roles": user.roles,
        },
    }


@router.get("/me")
def me(user: CurrentUser):
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "roles": user.roles,
    }
