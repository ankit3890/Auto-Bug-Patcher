"""AutoBug AI — Job ORM Model (tracks async pipeline execution)"""
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id"), index=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.QUEUED)

    # Progress tracking
    current_agent: Mapped[str | None] = mapped_column(String(100))
    completed_agents: Mapped[list | None] = mapped_column(JSON, default=list)
    failed_agent: Mapped[str | None] = mapped_column(String(100))
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)

    # Results
    root_cause_summary: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    error_message: Mapped[str | None] = mapped_column(Text)
    failure_classification: Mapped[str | None] = mapped_column(String(50))

    # Full pipeline state (JSON snapshot at each step)
    agent_outputs: Mapped[dict | None] = mapped_column(JSON)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    issue: Mapped["Issue"] = relationship("Issue", back_populates="jobs")  # noqa: F821
