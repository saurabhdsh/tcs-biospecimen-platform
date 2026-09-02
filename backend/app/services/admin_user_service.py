from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, DomainError, NotFoundError
from app.core.security import hash_password
from app.models.enums import AuditEventType, RoleName
from app.models.user import Role, User, UserRole
from app.services.audit_service import audit_service

ALLOWED_ROLES = {r.value for r in RoleName}


def serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "roles": user.roles,
        "is_active": user.is_active,
    }


class AdminUserService:
    def _load(self, db: Session, user_id: UUID) -> User:
        user = db.scalar(
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .where(User.id == user_id)
        )
        if user is None:
            raise NotFoundError("USER_NOT_FOUND", "User not found")
        return user

    def list_users(self, db: Session) -> list[dict]:
        users = list(
            db.scalars(
                select(User)
                .options(selectinload(User.user_roles).selectinload(UserRole.role))
                .where(User.is_active.is_(True))
                .order_by(User.full_name)
            )
        )
        return [serialize_user(u) for u in users]

    def create_user(
        self,
        db: Session,
        *,
        actor_id: UUID,
        email: str,
        full_name: str,
        password: str,
        roles: list[str],
    ) -> dict:
        email_n = email.strip().lower()
        names = [r.strip().upper() for r in roles]
        invalid = [r for r in names if r not in ALLOWED_ROLES]
        if invalid:
            raise DomainError("INVALID_ROLE", f"Unknown role: {', '.join(invalid)}")
        existing = db.scalar(select(User).where(User.email == email_n))
        if existing:
            raise ConflictError("EMAIL_IN_USE", "A user with this email already exists.")
        role_rows = list(db.scalars(select(Role).where(Role.name.in_(names))))
        if len(role_rows) != len(set(names)):
            raise DomainError("INVALID_ROLE", "One or more roles are not configured.")
        user = User(
            email=email_n,
            full_name=full_name.strip(),
            password_hash=hash_password(password),
            is_active=True,
        )
        db.add(user)
        db.flush()
        for role in role_rows:
            db.add(UserRole(user_id=user.id, role_id=role.id))
        db.flush()
        user = self._load(db, user.id)
        audit_service.record(
            db,
            event_type=AuditEventType.USER_CREATED,
            entity_type="User",
            entity_id=user.id,
            actor_user_id=actor_id,
            after_state={"email": user.email, "roles": user.roles, "full_name": user.full_name},
        )
        db.commit()
        return serialize_user(self._load(db, user.id))

    def delete_user(self, db: Session, *, actor_id: UUID, user_id: UUID) -> dict:
        if user_id == actor_id:
            raise DomainError("CANNOT_DELETE_SELF", "You cannot delete your own account.")
        user = self._load(db, user_id)
        if "ADMIN" in user.roles:
            admin_count = db.scalar(
                select(func.count())
                .select_from(User)
                .join(UserRole)
                .join(Role)
                .where(User.is_active.is_(True), Role.name == RoleName.ADMIN.value)
            )
            if (admin_count or 0) <= 1:
                raise DomainError("CANNOT_DELETE_LAST_ADMIN", "The last administrator cannot be deleted.")
        email = user.email
        nested = db.begin_nested()
        removed = False
        try:
            db.execute(delete(UserRole).where(UserRole.user_id == user.id))
            db.delete(user)
            db.flush()
            nested.commit()
            removed = True
        except IntegrityError:
            nested.rollback()
            user.is_active = False
            db.flush()
        audit_service.record(
            db,
            event_type=AuditEventType.USER_DELETED,
            entity_type="User",
            entity_id=user_id,
            actor_user_id=actor_id,
            before_state={"email": email},
            after_state={"removed": removed, "deactivated": not removed},
        )
        db.commit()
        return {"id": str(user_id), "removed": True}


admin_user_service = AdminUserService()
