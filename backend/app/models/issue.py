"""AutoBug AI — Issue ORM Model"""
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IssueSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueStatus(StrEnum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    REPRODUCING = "reproducing"
    FIXING = "fixing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id: Mapped[str] = mapped_column(String(36), ForeignKey("repositories.id"))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text)   # Raw user input
    severity: Mapped[IssueSeverity] = mapped_column(Enum(IssueSeverity), default=IssueSeverity.MEDIUM)
    status: Mapped[IssueStatus] = mapped_column(Enum(IssueStatus), default=IssueStatus.PENDING)

    # Structured data extracted by IssueAgent
    error_type: Mapped[str | None] = mapped_column(String(255))
    error_message: Mapped[str | None] = mapped_column(Text)
    stack_trace: Mapped[str | None] = mapped_column(Text)
    environment: Mapped[dict | None] = mapped_column(JSON)  # {os, python_version, ...}
    reproduction_steps: Mapped[list | None] = mapped_column(JSON)

    # Source tracking
    github_issue_url: Mapped[str | None] = mapped_column(Text)
    github_issue_number: Mapped[int | None] = mapped_column(Integer)
    jira_ticket: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    repository: Mapped["Repository"] = relationship("Repository", back_populates="issues")  # noqa: F821
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="issue")  # noqa: F821
    patches: Mapped[list["Patch"]] = relationship("Patch", back_populates="issue")  # noqa: F821
    pull_requests: Mapped[list["PullRequest"]] = relationship("PullRequest", back_populates="issue")  # noqa: F821
