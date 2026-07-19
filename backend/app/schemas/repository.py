"""
AutoBug AI — Pydantic Schemas: Repository
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RepositoryCreate(BaseModel):
    github_url: str
    default_branch: str = "main"


class RepositoryResponse(BaseModel):
    id: str
    github_url: str
    full_name: str
    name: str
    description: str | None
    default_branch: str
    languages: dict | None
    file_count: int
    loc: int
    index_status: str
    qdrant_collection: str | None
    last_indexed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
