"""
AutoBug AI — Shared Agent State Schema
========================================
TypedDict that flows through all agents in the LangGraph pipeline.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AutoBugState(TypedDict, total=False):
    # ── Inputs ──────────────────────────────────────────────────────────────
    repo_url: str                        # GitHub URL of the repository
    issue_text: str                      # Raw bug report / issue description
    issue_id: str                        # DB issue UUID
    job_id: str                          # DB job UUID

    # ── Repository ──────────────────────────────────────────────────────────
    repo_path: str                       # Local clone path
    repo_id: str                         # DB repository UUID
    repo_languages: dict[str, int]       # {"Python": 80, "JS": 20}
    repo_file_tree: list[str]            # Flat list of repo file paths
    qdrant_collection: str               # Qdrant collection name

    # ── Issue Analysis ───────────────────────────────────────────────────────
    issue_structured: dict[str, Any]     # Parsed: error_type, stack_trace, severity
    search_queries: list[str]            # Planner-generated search queries

    # ── Code Retrieval ───────────────────────────────────────────────────────
    retrieved_chunks: list[dict]         # Top-k RAG results

    # ── Environment & Build ─────────────────────────────────────────────────
    runtime_info: dict[str, Any]         # {language, version, package_manager}
    sandbox_session_id: str              # Active sandbox container ID
    build_result: dict[str, Any]         # {success, stdout, stderr}

    # Sprint 3: environment validator result
    environment_result: dict[str, Any]   # EnvironmentResult schema format

    # ── Sprint 1: Decoupled Reproduction ─────────────────────────────────────
    # runtime bug reproduction ONLY — no pytest/lint here
    reproduction_result: dict[str, Any]  # ReproductionResult schema format

    # ── Sprint 8: Evidence Catalog ────────────────────────────────────────────
    # keyed by EV-xxx ID, value is EvidenceItem schema
    evidence_catalog: dict[str, Any]

    # ── Localization ────────────────────────────────────────────────────────
    fault_files: list[str]               # Narrowed list of suspected files
    fault_functions: list[str]           # Suspected function names

    # ── Root Cause ──────────────────────────────────────────────────────────
    root_cause: dict[str, Any]           # RootCauseAnalysis schema format

    # ── Patch ───────────────────────────────────────────────────────────────
    patch: dict[str, Any]                # patch + PerformanceImpact schema format

    # ── Sprint 7: Performance Analysis ───────────────────────────────────────
    performance_analysis: dict[str, Any]  # PerformanceAnalysis schema format

    # ── Sprint 1: Decoupled Validation ───────────────────────────────────────
    # test/lint/static/build validation ONLY — separate from reproduction
    static_analysis_result: dict[str, Any]
    generated_tests: dict[str, Any]      # {test_code, test_file}
    test_result: dict[str, Any]          # {passed, stdout, stderr}
    validation_result: dict[str, Any]    # ValidationResult schema format

    # ── Reviewer ────────────────────────────────────────────────────────────
    reviewer_feedback: dict[str, Any]    # ReviewResult schema format (Sprint 4)

    # ── Risk & Metrics ──────────────────────────────────────────────────────
    risk_analysis: dict[str, Any]        # RiskAnalysis schema format
    metrics: dict[str, Any]              # ExecutionMetrics schema format

    # ── Sprint 5: Decision Engine ─────────────────────────────────────────────
    decision: dict[str, Any]             # DecisionResult schema format

    # ── Git & PR ─────────────────────────────────────────────────────────────
    branch_name: str
    commit_sha: str
    pr_url: str
    pr_number: int

    # ── Report ──────────────────────────────────────────────────────────────
    report: str                          # Final Markdown report
    report_html: str                     # Sprint 10: HTML export
    report_path: str                     # Sprint 10: file path to saved report

    # ── Pipeline Control ────────────────────────────────────────────────────
    error: str | None                    # Set when an agent fails
    failed_agent: str | None             # Which agent failed
    steps_completed: list[str]           # Agents that completed successfully
    steps_skipped: list[str]             # Agents that were skipped (Sprint 6)
    steps_failed: list[str]              # Agents that failed (Sprint 6)
    test_validation_result: dict[str, Any]
    test_gen_retries: int
    failure_classification: str

