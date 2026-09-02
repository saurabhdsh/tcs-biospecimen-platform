from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Requirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "requirements"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    component: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="requirement")


class TestCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "test_cases"
    __table_args__ = (UniqueConstraint("requirement_id", "code", name="uq_testcase_per_requirement"),)

    requirement_id: Mapped[UUID] = mapped_column(ForeignKey("requirements.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    requirement: Mapped[Requirement] = relationship(back_populates="test_cases")
    executions: Mapped[list["TestExecution"]] = relationship(back_populates="test_case")


class TestExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "test_executions"

    test_case_id: Mapped[UUID] = mapped_column(ForeignKey("test_cases.id"), nullable=False, index=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)
    executed_by: Mapped[str | None] = mapped_column(String(128))
    notes: Mapped[str | None] = mapped_column(Text)

    test_case: Mapped[TestCase] = relationship(back_populates="executions")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="test_execution")


class Evidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evidence"

    test_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("test_executions.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_ref: Mapped[str | None] = mapped_column(String(255))

    test_execution: Mapped[TestExecution] = relationship(back_populates="evidence")
