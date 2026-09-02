from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, DomainError, ForbiddenError, NotFoundError
from app.models.enums import AuditEventType, ExceptionDisposition, ExceptionStatus, SampleStatus
from app.models.environmental import EnvironmentalEvent
from app.models.exception import ExceptionCase, ExceptionResolution, ExceptionStatusHistory
from app.models.user import User
from app.services.audit_service import audit_service
from app.services.sample_service import sample_service
from app.services.state_machine import lock_sample, state_machine


class ExceptionService:
    def _next_case_number(self, db: Session) -> str:
        year = datetime.now(timezone.utc).year
        count = db.scalar(select(func.count(ExceptionCase.id))) or 0
        return f"EXC-{year}-{count + 1:05d}"

    def create_from_event(
        self, db: Session, *, event: EnvironmentalEvent, actor_id: UUID, commit: bool = True
    ) -> ExceptionCase:
        sample = lock_sample(db, event.sample_id)
        now = datetime.now(timezone.utc)
        case = ExceptionCase(
            case_number=self._next_case_number(db),
            sample_id=sample.id,
            source_event_id=event.id,
            status=ExceptionStatus.OPEN.value,
            reason=(
                f"Temperature excursion {event.measured_value}{event.unit} "
                f"(acceptable {event.acceptable_min}–{event.acceptable_max}{event.unit})"
            ),
            opened_by=actor_id,
            opened_at=now,
            created_by=actor_id,
        )
        db.add(case)
        db.flush()
        db.add(
            ExceptionStatusHistory(
                exception_id=case.id,
                from_status=None,
                to_status=ExceptionStatus.OPEN.value,
                comment="Opened from environmental excursion",
                created_by=actor_id,
            )
        )
        if sample.status != SampleStatus.QUARANTINED:
            before = {"status": sample.status}
            if sample.status == SampleStatus.CHECKED_OUT:
                raise DomainError(
                    "CANNOT_QUARANTINE_CHECKED_OUT",
                    "Return the sample to storage before quarantining from an environmental event.",
                )
            if sample.status in {SampleStatus.IN_STORAGE, SampleStatus.ACCESSIONED, SampleStatus.RECEIVED, SampleStatus.RELEASED}:
                # Direct assign if already allowed, otherwise force via IN_STORAGE path where needed
                if sample.status == SampleStatus.RECEIVED:
                    state_machine.transition(sample, SampleStatus.ACCESSIONED)
                if sample.status == SampleStatus.ACCESSIONED:
                    state_machine.transition(sample, SampleStatus.IN_STORAGE)
                if sample.status == SampleStatus.RELEASED:
                    sample.status = SampleStatus.QUARANTINED.value
                else:
                    state_machine.transition(sample, SampleStatus.QUARANTINED)
            audit_service.record(
                db,
                event_type=AuditEventType.SAMPLE_QUARANTINED,
                entity_type="Sample",
                entity_id=sample.id,
                actor_user_id=actor_id,
                before_state=before,
                after_state={"status": sample.status},
                reason=case.reason,
            )
        audit_service.record(
            db,
            event_type=AuditEventType.EXCEPTION_CREATED,
            entity_type="ExceptionCase",
            entity_id=case.id,
            actor_user_id=actor_id,
            after_state={"case_number": case.case_number, "sample_id": sample.sample_id},
        )
        if commit:
            db.commit()
        return case

    def get(self, db: Session, exception_id: UUID) -> ExceptionCase:
        case = db.scalar(
            select(ExceptionCase)
            .options(
                selectinload(ExceptionCase.sample),
                selectinload(ExceptionCase.source_event),
                selectinload(ExceptionCase.status_history),
                selectinload(ExceptionCase.resolution),
            )
            .where(ExceptionCase.id == exception_id)
        )
        if case is None:
            raise NotFoundError("EXCEPTION_NOT_FOUND", "Exception not found")
        return case

    def list_cases(self, db: Session, status: str | None = None) -> list[ExceptionCase]:
        stmt = select(ExceptionCase).options(selectinload(ExceptionCase.sample)).order_by(ExceptionCase.opened_at.desc())
        if status:
            stmt = stmt.where(ExceptionCase.status == status)
        return list(db.scalars(stmt))

    def resolve(
        self,
        db: Session,
        *,
        exception_id: UUID,
        actor: User,
        resolution_comment: str,
        disposition: str,
    ) -> ExceptionCase:
        if "REVIEWER" not in actor.roles and "ADMIN" not in actor.roles:
            raise ForbiddenError("FORBIDDEN", "Only Reviewer or Admin may resolve exceptions.")
        if not resolution_comment or not resolution_comment.strip():
            raise DomainError("RESOLUTION_COMMENT_REQUIRED", "resolution_comment is required.")
        try:
            disp = ExceptionDisposition(disposition)
        except ValueError as exc:
            raise DomainError(
                "INVALID_DISPOSITION",
                "disposition must be RELEASE_TO_INVENTORY, RELEASE_WITH_RESTRICTION, or DISPOSE.",
            ) from exc
        case = db.scalar(select(ExceptionCase).where(ExceptionCase.id == exception_id).with_for_update())
        if case is None:
            raise NotFoundError("EXCEPTION_NOT_FOUND", "Exception not found")
        if case.status in {ExceptionStatus.RESOLVED, ExceptionStatus.CLOSED}:
            raise ConflictError("EXCEPTION_ALREADY_RESOLVED", "Exception is already resolved.")
        sample = lock_sample(db, case.sample_id)
        now = datetime.now(timezone.utc)
        target = {
            ExceptionDisposition.RELEASE_TO_INVENTORY: SampleStatus.IN_STORAGE,
            ExceptionDisposition.RELEASE_WITH_RESTRICTION: SampleStatus.RELEASED,
            ExceptionDisposition.DISPOSE: SampleStatus.DISPOSED,
        }[disp]
        before = {"status": sample.status, "exception_status": case.status}
        if sample.status == SampleStatus.QUARANTINED:
            state_machine.transition(sample, target)
        sample.restriction_flag = disp == ExceptionDisposition.RELEASE_WITH_RESTRICTION
        case.status = ExceptionStatus.RESOLVED.value
        case.closed_at = now
        db.add(
            ExceptionStatusHistory(
                exception_id=case.id,
                from_status=ExceptionStatus.OPEN.value,
                to_status=ExceptionStatus.RESOLVED.value,
                comment=resolution_comment.strip(),
                created_by=actor.id,
            )
        )
        db.add(
            ExceptionResolution(
                exception_id=case.id,
                resolver_user_id=actor.id,
                resolved_at=now,
                resolution_comment=resolution_comment.strip(),
                disposition=disp.value,
                resulting_sample_status=target.value,
                created_by=actor.id,
            )
        )
        audit_service.record(
            db,
            event_type=AuditEventType.EXCEPTION_RESOLVED,
            entity_type="ExceptionCase",
            entity_id=case.id,
            actor_user_id=actor.id,
            reason=resolution_comment.strip(),
            before_state=before,
            after_state={
                "disposition": disp.value,
                "sample_status": sample.status,
                "case_status": case.status,
            },
        )
        db.commit()
        return self.get(db, case.id)


exception_service = ExceptionService()
