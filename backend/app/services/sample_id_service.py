from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sample import SampleIdSequence


class SampleIdService:
    def next_id(self, db: Session, year: int | None = None) -> str:
        year = year or datetime.now(timezone.utc).year
        seq = db.scalar(
            select(SampleIdSequence).where(SampleIdSequence.year == year).with_for_update()
        )
        if seq is None:
            seq = SampleIdSequence(year=year, next_value=1)
            db.add(seq)
            db.flush()
            seq = db.scalar(
                select(SampleIdSequence).where(SampleIdSequence.year == year).with_for_update()
            )
        value = seq.next_value
        seq.next_value = value + 1
        db.flush()
        return f"SMP-{year}-{value:06d}"


sample_id_service = SampleIdService()
