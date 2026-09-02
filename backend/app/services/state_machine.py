from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models.enums import ALLOWED_SAMPLE_TRANSITIONS, SampleStatus
from app.models.sample import Sample


class SampleStateMachine:
    def assert_transition(self, sample: Sample, target: SampleStatus) -> None:
        current = SampleStatus(sample.status)
        allowed = ALLOWED_SAMPLE_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise DomainError(
                "INVALID_STATUS_TRANSITION",
                f"Cannot transition sample {sample.sample_id} from {current} to {target}.",
                details={"from": current, "to": target, "allowed": sorted(s.value for s in allowed)},
            )

    def transition(self, sample: Sample, target: SampleStatus) -> None:
        self.assert_transition(sample, target)
        sample.status = target.value
        sample.updated_at = datetime.now(timezone.utc)


state_machine = SampleStateMachine()


def lock_sample(db: Session, sample_id: UUID) -> Sample:
    sample = db.scalar(select(Sample).where(Sample.id == sample_id).with_for_update())
    if sample is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("SAMPLE_NOT_FOUND", "Sample not found")
    return sample
