from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.models.enums import AuditEventType
from app.models.user import User, UserRole
from app.services.audit_service import audit_service


class AuthService:
    def authenticate(self, db: Session, email: str, password: str) -> tuple[User, str]:
        user = db.scalar(
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .where(User.email == email.lower())
        )
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            raise UnauthorizedError("INVALID_CREDENTIALS", "Invalid email or password")
        token = create_access_token(user_id=user.id, email=user.email, roles=user.roles)
        audit_service.record(
            db,
            event_type=AuditEventType.LOGIN,
            entity_type="User",
            entity_id=user.id,
            actor_user_id=user.id,
            after_state={"email": user.email, "roles": user.roles},
        )
        db.commit()
        return user, token

    def get_user(self, db: Session, user_id: UUID) -> User:
        user = db.scalar(
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .where(User.id == user_id)
        )
        if user is None or not user.is_active:
            raise NotFoundError("USER_NOT_FOUND", "User not found")
        return user

    def require_roles(self, user: User, allowed: set[str]) -> None:
        if not allowed.intersection(user.roles):
            raise ForbiddenError(
                "FORBIDDEN",
                "You do not have permission to perform this action.",
                details={"required_roles": sorted(allowed), "actual_roles": user.roles},
            )


auth_service = AuthService()
