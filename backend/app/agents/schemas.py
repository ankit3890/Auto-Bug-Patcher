"""
AutoBug AI — Shared State Pydantic Schemas
============================================
Defines structured objects for agent states.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ── Sprint 1: Validation stage tracking ─────────────────────────────────────

class ValidationStageDetails(BaseModel):
    status: str = "pending"  # pending | passed | failed | error | skipped
    command: str = "N/A"
    exit_code: int | None = None
    duration_seconds: float | None = None
    stdout: str = ""
    stderr: str = ""
    reason: str | None = None


class ValidationResult(BaseModel):
    """Decoupled validation result — only covers test/lint/static/build stages."""
    build_passed: bool = False
    lint_passed: bool = False
    tests_executed: bool = False
    tests_passed: bool = False
    coverage: float | None = None
    failed_reason: str | None = None
    stages: dict[str, ValidationStageDetails] = Field(default_factory=dict)


# Sprint 1 legacy alias kept for backward compat
ValidationState = ValidationResult


# ── Sprint 1: Runtime reproduction result ────────────────────────────────────

class ReproductionResult(BaseModel):
    """Result of the runtime bug reproduction attempt — separate from validation."""
    reproduced: bool = False
    environment_ready: bool = True
    method: str = "sandbox_command"  # sandbox_command | browser | api | manual
    command: str = ""
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    observed_behavior: str = ""
    expected_behavior: str = ""
    browser_logs: str = ""
    screenshots: list[str] = Field(default_factory=list)
    api_logs: list[str] = Field(default_factory=list)
    terminal_logs: str = ""
    reproduction_failed_reason: str | None = None
    request_details: str | None = None


# Sprint 1 legacy alias kept for backward compat
ReproductionEvidence = ReproductionResult


# ── Sprint 4: Evidence-only reviewer output ───────────────────────────────────

class ReviewResult(BaseModel):
    """Structured reviewer output — every claim must reference evidence."""
    approved: bool = False
    recommendation: str = "request_changes"  # approved | reject | request_changes
    overall_score: float = 0.0
    correctness_score: float = 0.0
    security_score: float = 0.0
    quality_score: float = 0.0
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    comments: list[str] = Field(default_factory=list)
    critical_issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)  # e.g. ["EV-001", "EV-003"]
    confidence: float = 0.0


# Sprint 4 backward compat alias
ReviewEvaluation = ReviewResult


# ── Risk, performance, metrics, root cause ────────────────────────────────────

class RiskAnalysis(BaseModel):
    risk_level: str = "low"  # low | medium | high
    breaking_api: bool = False
    database_changes: bool = False
    dependency_changes: bool = False
    regression_risk: float = 0.0
    reasoning: str = ""


class PerformanceImpact(BaseModel):
    """Sprint 7: component-wise performance impact from patch."""
    client_complexity_before: str = "O(1)"
    client_complexity_after: str = "O(1)"
    network_complexity_before: str = "None"
    network_complexity_after: str = "None"
    backend_complexity_before: str = "Existing"
    backend_complexity_after: str = "Existing"
    memory_impact: str = "No change"
    latency_impact: str = "Expected unchanged"
    # Legacy single-string fields kept for backward compat
    complexity_before: str = "N/A"
    complexity_after: str = "N/A"


class ExecutionMetrics(BaseModel):
    node_durations: dict[str, float] = Field(default_factory=dict)
    token_counts: dict[str, int] = Field(default_factory=dict)
    costs: dict[str, float] = Field(default_factory=dict)
    total_duration_seconds: float = 0.0
    total_cost: float = 0.0


class RootCauseAnalysis(BaseModel):
    summary: str = ""
    observed_behavior: str = ""
    inferred_cause: str = ""
    fault_file: str = ""
    fault_line: int | None = None
    fault_function: str = ""
    root_cause_category: str = ""
    confidence: float = 0.0
    fix_suggestion: str = ""
    evidence_ids: list[str] = Field(default_factory=list)  # Sprint 8


# ── Sprint 5: Decision engine output ─────────────────────────────────────────

class DecisionResult(BaseModel):
    """Programmatic merge/ship decision."""
    decision: str = "Needs Review"  # Ready for Merge | Needs Review | Manual Review | Reject
    status: str = "needs_review"
    reason: str = ""
    blocking_factors: list[str] = Field(default_factory=list)
    allow_commit: bool = False
    allow_pr: bool = False
    allow_report: bool = True
    allow_retry: bool = False


# ── Sprint 7: Structured performance analysis ─────────────────────────────────

class ComponentPerformance(BaseModel):
    component: str = ""
    complexity_before: str = "N/A"
    complexity_after: str = "N/A"
    network_before: str = "N/A"
    network_after: str = "N/A"
    memory_before: str = "N/A"
    memory_after: str = "N/A"
    latency_delta: str = "No change"


class PerformanceAnalysis(BaseModel):
    components: list[ComponentPerformance] = Field(default_factory=list)
    summary: str = ""
    overall_latency_impact: str = "Expected unchanged"


# ── Sprint 3: Environment validator output ────────────────────────────────────

class EnvironmentResult(BaseModel):
    ready: bool = False
    installed_packages: list[str] = Field(default_factory=list)
    missing_packages: list[str] = Field(default_factory=list)
    fixed_packages: list[str] = Field(default_factory=list)
    setup_logs: str = ""
    error: str | None = None


# ── Sprint 8: Evidence catalog entry ─────────────────────────────────────────

class EvidenceItem(BaseModel):
    id: str = ""          # e.g. "EV-001"
    kind: str = ""        # browser_log | http_response | stacktrace | code_snippet | terminal_log
    description: str = ""
    content: str = ""
    source_agent: str = ""

