"""
AutoBug AI — Pydantic Schemas: Job
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: str
    issue_id: str
    celery_task_id: str | None
    status: str
    current_agent: str | None
    completed_agents: list | None
    failed_agent: str | None
    progress_percent: float
    root_cause_summary: str | None
    confidence_score: float | None
    error_message: str | None
    agent_outputs: dict | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True
