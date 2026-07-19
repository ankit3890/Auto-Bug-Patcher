"""AutoBug AI — Patch ORM Model"""
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PatchStatus(StrEnum):
    GENERATED = "generated"
    VALIDATING = "validating"
    VALIDATED = "validated"
    REJECTED = "rejected"
    APPLIED = "applied"


class Patch(Base):
    __tablename__ = "patches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_id: Mapped[str] = mapped_column(String(36), ForeignKey("issues.id"), index=True)
    status: Mapped[PatchStatus] = mapped_column(Enum(PatchStatus), default=PatchStatus.GENERATED)

    # Patch content
    unified_diff: Mapped[str | None] = mapped_column(Text)          # Full unified diff
    modified_files: Mapped[list | None] = mapped_column(JSON)       # List of changed file paths
    patch_summary: Mapped[str | None] = mapped_column(Text)         # Human-readable explanation

    # Root cause info
    root_cause: Mapped[str | None] = mapped_column(Text)
    fault_location: Mapped[str | None] = mapped_column(String(500)) # file:line
    confidence_score: Mapped[float | None] = mapped_column(Float)

    # Validation results
    static_analysis_passed: Mapped[bool | None] = mapped_column(Boolean)
    tests_passed: Mapped[bool | None] = mapped_column(Boolean)
    test_results: Mapped[dict | None] = mapped_column(JSON)
    reviewer_feedback: Mapped[str | None] = mapped_column(Text)
    validation_details: Mapped[dict | None] = mapped_column(JSON)

    # Generated test
    regression_test: Mapped[str | None] = mapped_column(Text)
    regression_test_file: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    issue: Mapped["Issue"] = relationship("Issue", back_populates="patches")  # noqa: F821
