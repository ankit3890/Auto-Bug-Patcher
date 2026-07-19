"""
AutoBug AI — Pydantic Schemas: Issue
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class IssueCreate(BaseModel):
    repository_id: str
    title: str
    description: str
    severity: str = "medium"
    github_issue_url: str | None = None
    github_issue_number: int | None = None


class IssueResponse(BaseModel):
    id: str
    repository_id: str
    title: str
    description: str
    severity: str
    status: str
    error_type: str | None
    error_message: str | None
    stack_trace: str | None
    environment: dict | None
    reproduction_steps: list | None
    github_issue_url: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
