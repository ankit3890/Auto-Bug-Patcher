"""
AutoBug AI — Pydantic Schemas: Patch
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PatchResponse(BaseModel):
    id: str
    issue_id: str
    status: str
    unified_diff: str | None
    modified_files: list | None
    patch_summary: str | None
    root_cause: str | None
    fault_location: str | None
    confidence_score: float | None
    static_analysis_passed: bool | None
    tests_passed: bool | None
    test_results: dict | None
    reviewer_feedback: str | None
    regression_test: str | None
    created_at: datetime

    class Config:
        from_attributes = True
