from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.traceability import Requirement, TestCase, TestExecution


class TraceabilityService:
    def matrix(self, db: Session) -> list[dict]:
        requirements = list(
            db.scalars(
                select(Requirement)
                .options(
                    selectinload(Requirement.test_cases)
                    .selectinload(TestCase.executions)
                    .selectinload(TestExecution.evidence)
                )
                .order_by(Requirement.code)
            )
        )
        rows = []
        for req in requirements:
            for tc in req.test_cases:
                executions = sorted(tc.executions, key=lambda e: e.executed_at, reverse=True)
                last = executions[0] if executions else None
                rows.append(
                    {
                        "requirement_code": req.code,
                        "requirement_title": req.title,
                        "component": req.component,
                        "requirement_description": req.description,
                        "test_case_code": tc.code,
                        "test_case_title": tc.title,
                        "last_run_at": last.executed_at.isoformat() if last else None,
                        "last_result": last.result if last else "NOT_RUN",
                        "executed_by": last.executed_by if last else None,
                        "evidence": [
                            {"title": ev.title, "details": ev.details, "artifact_ref": ev.artifact_ref}
                            for ev in (last.evidence if last else [])
                        ],
                    }
                )
        return rows


traceability_service = TraceabilityService()
