from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import auth_service

bearer = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_correlation_id(x_request_id: Annotated[str | None, Header()] = None) -> str | None:
    return x_request_id


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError()
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError) as exc:
        raise UnauthorizedError("INVALID_TOKEN", "Invalid or expired token") from exc
    return auth_service.get_user(db, user_id)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str):
    allowed = set(roles)

    def _dep(user: CurrentUser) -> User:
        auth_service.require_roles(user, allowed)
        return user

    return _dep


OperatorUser = Annotated[User, Depends(require_roles("OPERATOR", "ADMIN"))]
ReviewerUser = Annotated[User, Depends(require_roles("REVIEWER", "ADMIN"))]
AdminUser = Annotated[User, Depends(require_roles("ADMIN"))]
AnyAuthUser = CurrentUser
