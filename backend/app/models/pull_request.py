"""AutoBug AI — Pull Request ORM Model"""
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PRStatus(StrEnum):
    OPENED = "opened"
    UNDER_REVIEW = "under_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    MERGED = "merged"
    CLOSED = "closed"


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id"), index=True)

    github_pr_number: Mapped[int | None] = mapped_column(Integer)
    github_pr_url: Mapped[str | None] = mapped_column(Text)
    github_branch: Mapped[str | None] = mapped_column(String(255))
    github_commit_sha: Mapped[str | None] = mapped_column(String(40))

    title: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str | None] = mapped_column(Text)   # Full PR description with report
    status: Mapped[PRStatus] = mapped_column(Enum(PRStatus), default=PRStatus.OPENED)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    issue: Mapped["Issue"] = relationship("Issue", back_populates="pull_requests")  # noqa: F821
