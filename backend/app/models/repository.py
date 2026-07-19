"""AutoBug AI — Repository ORM Model"""
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IndexStatus(StrEnum):
    PENDING = "pending"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"
    OUTDATED = "outdated"


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    github_url: Mapped[str] = mapped_column(Text, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)  # owner/repo
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    languages: Mapped[dict | None] = mapped_column(JSON)        # {"Python": 80, "JS": 20}
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    loc: Mapped[int] = mapped_column(Integer, default=0)        # Lines of code
    index_status: Mapped[IndexStatus] = mapped_column(Enum(IndexStatus), default=IndexStatus.PENDING)
    qdrant_collection: Mapped[str | None] = mapped_column(String(255))
    local_path: Mapped[str | None] = mapped_column(Text)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_commit_sha: Mapped[str | None] = mapped_column(String(40))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    owner: Mapped["User"] = relationship("User", back_populates="repositories")  # noqa: F821
    issues: Mapped[list["Issue"]] = relationship("Issue", back_populates="repository")  # noqa: F821
