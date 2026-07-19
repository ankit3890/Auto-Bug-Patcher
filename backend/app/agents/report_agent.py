"""
AutoBug AI — Report Agent
===========================
Generates a comprehensive Markdown report from the complete pipeline state.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from datetime import UTC, datetime

from app.agents.state import AutoBugState

logger = logging.getLogger(__name__)


async def report_agent(state: AutoBugState) -> AutoBugState:
    """Generate comprehensive bug fix report."""
    logger.info("[ReportAgent] Generating report")
    try:
        report = _build_report(state)
        logger.info("[ReportAgent] Report generated (%d chars)", len(report))
        # Sprint 10: generate HTML export
        issue_id = state.get("issue_id", "unknown")
        report_html, report_path = _export_html(report, issue_id)
        return {
            **state,
            "report": report,
            "report_html": report_html,
            "report_path": report_path,
            "steps_completed": [*(state.get("steps_completed") or []), "report_agent"],
            "validation_result": {
                "static_analysis": state.get("static_analysis_result") or {},
                "tests": state.get("test_result") or {},
                "review": state.get("reviewer_feedback") or {},
                "overall_passed": (
                    (state.get("test_result") or {}).get("passed", False)
                    and (state.get("reviewer_feedback") or {}).get("approved", False)
                ),
            },
            "error": None,
        }
    except Exception as exc:
        logger.error("[ReportAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "report": f"Report generation failed: {exc}",
            "steps_completed": [*(state.get("steps_completed") or []), "report_agent"],
        }


from app.core.confidence import calculate_confidence, calculate_confidence_matrix
from jinja2 import Template

JINJA_TEMPLATE = """# AutoBug AI — Bug Fix Report

**Generated:** {{ now }}
**Issue ID:** {{ issue_id }}
**Repository:** {{ repo_url }}

---

## Executive Summary

| Field | Value |
|-------|-------|
| Error Type | `{{ issue.error_type | default('Unknown') }}` |
| Severity | **{{ issue.severity | default('medium') | upper }}** |
| Failure Classification | **{{ failure_classification }}** |
| Root Cause Confidence | {{ "%.0f"|format(matrix.root_cause_confidence * 100) }}% |
| Patch Confidence | {{ "%.0f"|format(matrix.patch_confidence * 100) }}% |
| Validation Confidence | {{ "%.0f"|format(matrix.validation_confidence * 100) }}% |
| **Overall Release Confidence** | **{{ "%.0f"|format(matrix.overall_release_confidence * 100) }}%** |
| Confidence Tier | {{ matrix.confidence_tier | default('N/A') }} |
| Bug Reproduced | {{ "Yes" if repro.reproduced else "No" if (repro.reproduced is sameas(false) and not repro.reproduction_failed_reason) else "FAILED (Sandbox Environment Error)" }} |
| Fix Status | {{ "Tests Passing" if tests_passed else "Tests Need Review" if test_result.get("command") else "Not Executed" }} |
| Patch Correctness | **{{ patch_correctness }}** |
{% if validation_blocked_reason %}
| Validation Blocked Reason | *{{ validation_blocked_reason }}* |
{% endif %}
| Pull Request | {{ pr_section }} |

### Confidence Breakdown
{% for item in matrix.confidence_explanation | default([]) %}
- {{ item }}
{% else %}
- No confidence breakdown available.
{% endfor %}

### Evidence Quality Assessment
| Evidence Dimension | Quality Status |
|--------------------|----------------|
| **Static Analysis** | {{ matrix.evidence_quality.static_analysis }} |
| **Runtime Sandbox Reproduction** | {{ matrix.evidence_quality.runtime_reproduction }} |
| **Unit Verification Tests** | {{ matrix.evidence_quality.unit_tests }} |
| **Source Code Analysis** | {{ matrix.evidence_quality.source_code_analysis }} |
| **Patch/Code Review Validation** | {{ matrix.evidence_quality.patch_validation }} |

---

## Root Cause Analysis

**Summary:** {{ root_cause.summary | default('N/A') }}

**Observed Behavior (Facts):**
{{ root_cause.observed_behavior | default('No concrete observed behavior logs available.') }}

**Inferred Cause (Conclusions):**
{{ root_cause.inferred_cause | default('No inferred cause concluded.') }}

**Fault Location:**
- File: `{{ root_cause.fault_file | default('unknown') }}`
- Line: {{ root_cause.fault_line | default('?') }}
- Function: `{{ root_cause.fault_function | default('unknown') }}`
- Category: `{{ root_cause.root_cause_category | default('unknown') }}`
- Confidence: **{{ "%.0f"|format(matrix.overall_release_confidence * 100) }}%**

---

## Generated Fix

**Summary:** {{ patch.patch_summary | default('N/A') }}

### Complexity & Performance Impact
| Component | Before Fix | After Fix |
|-----------|------------|-----------|
| **Client Processing** | `{{ patch.client_complexity_before | default('O(1)') }}` | `{{ patch.client_complexity_after | default('O(1)') }}` |
| **Network Overhead** | `{{ patch.network_complexity_before | default('None') }}` | `{{ patch.network_complexity_after | default('None') }}` |
| **Backend Search** | `{{ patch.backend_complexity_before | default('Existing') }}` | `{{ patch.backend_complexity_after | default('Existing') }}` |
| **Latency Impact** | - | `{{ patch.latency_impact | default('Expected unchanged') }}` |

**Modified Files:**
{% for f in patch.modified_files %}
- `{{ f }}`
{% else %}
- None
{% endfor %}

```diff
{{ patch.unified_diff | default('No patch generated') }}
```

---

## Environment Health

{% if env_result.tool_results %}
| Tool | Status | Version / Error |
|------|--------|-----------------|
{% for row in env_result.tool_results %}
| **{{ row.tool }}** | {{ row.status }} | {{ row.version or row.get('error', 'N/A') }} |
{% endfor %}
{% if env_result.blocking_reason %}

**Blocked:** {{ env_result.blocking_reason }}
{% endif %}
{% else %}
Environment validation not executed.
{% endif %}

---


| Assessment | Value |
|------------|-------|
| **Release Risk Level** | {{ risk.risk_level | default('low') | upper }} |
| **Regression Probability** | {{ "%.0f"|format(risk.regression_risk | default(0) * 100) }}% |
| **Database Migrations** | {{ "Yes (DB Changes Detected)" if risk.database_changes else "None" }} |
| **API Signature Changes** | {{ "Yes (API Changes Detected)" if risk.breaking_api else "None" }} |
| **Dependency Changes** | {{ "Yes (Dependency Changes Detected)" if risk.dependency_changes else "None" }} |

**Release Reasoning:**
{{ risk_reasoning }}

---

## Validation Results

### Tests {% if tests_passed %}(Passed){% else %}(Failed){% endif %}
- **Status:** {{ test_status }}
- **Exit Code:** {{ test_result.exit_code | default('N/A') }}
- **Command:** `{{ test_result.command | default('N/A') }}`
{% if test_reason %}
- **Reason:** {{ test_reason }}
{% endif %}

<details>
<summary>Test Output</summary>

```
{{ test_result.stdout | default('') | truncate(3000) }}
{{ test_result.stderr | default('') | truncate(1000) }}
```
</details>

### Static Analysis {% if static.passed %}(Passed){% else %}(Warnings/Issues){% endif %}
- **Passed:** {{ static.passed | default(true) }}
- **Issues Found:** {{ static.issues | length }}

### Code Review {% if reviewer.approved %}(Approved){% else %}(Needs Review){% endif %}
- **Approved:** {{ reviewer.approved | default(false) }}
- **Overall Score:** {{ reviewer.overall_score | default('N/A') }}/10
- **Correctness:** {{ reviewer.correctness_score | default('N/A') }}/10
- **Security:** {{ reviewer.security_score | default('N/A') }}/10
- **Quality/Maintainability:** {{ reviewer.quality_score | default('N/A') }}/10

**Reviewer Comments:**
{% for c in reviewer.comments %}
- {{ c }}
{% else %}
- No comments
{% endfor %}

---

## Validation & Reproduction Evidence

### Sandbox Reproduction Details
* **Reproduction Status:** {{ "Successfully Reproduced in Sandbox" if repro.reproduced else "FAILED (Sandbox Environment Error)" if repro.reproduction_failed_reason else "Not Reproduced" }}
{% if repro.reproduction_failed_reason %}
* **Environment Issue:** `{{ repro.reproduction_failed_reason }}`
* **Note:** The UI reproduction could not be completed automatically. Root cause was inferred from source code static analysis.
{% endif %}
* **Command Executed:** `{{ repro.command | default('N/A') }}`
* **Exit Code:** `{{ repro.exit_code | default('N/A') }}`

<details>
<summary>Observed Reproduction Logs (Facts)</summary>

```
{{ repro.stdout | default('') | truncate(3000) }}
{{ repro.stderr | default('') | truncate(1000) }}
```
</details>

---

## Pipeline Execution Metrics

| Node Name | Execution Duration | Execution Cost |
|-----------|--------------------|----------------|
{% for name, duration in metrics.node_durations.items() %}
| **{{ name }}** | {{ "%.2f"|format(duration) }} sec | ${{ "%.5f"|format(metrics.costs.get(name, 0.0)) }} |
{% endfor %}
| **TOTAL** | **{{ "%.2f"|format(metrics.total_duration_seconds) }} sec** | **${{ "%.5f"|format(metrics.total_cost) }}** |

---

## Decision

| Field | Value |
|-------|-------|
| **Recommendation** | **{{ decision.decision | default('Needs Review') }}** |
| **Reason** | {{ decision.reason | default('No decision computed.') }} |
{% if decision.blocking_factors %}

**Blocking Factors:**
{% for factor in decision.blocking_factors %}
- {{ factor }}
{% endfor %}
{% endif %}
{% if decision.next_steps %}

**Next Steps:**
{% for step in decision.next_steps %}
{{ loop.index }}. {{ step }}
{% endfor %}
{% endif %}

---

## Pipeline Status

| Agent | Status |
|-------|--------|
{% for agent, status in pipeline_status %}
| {{ agent }} | {{ status }} |
{% endfor %}

**Summary:** {{ steps_summary.completed }} Completed / {{ steps_summary.skipped }} Skipped / {{ steps_summary.failed }} Failed / {{ total_agents }} Total

---

## Evidence Catalog

{% if evidence_catalog %}
| ID | Kind | Description | Source Agent |
|----|------|-------------|--------------|
{% for eid, item in evidence_catalog.items() %}
| **{{ eid }}** | {{ item.kind }} | {{ item.description }} | {{ item.source_agent }} |
{% endfor %}
{% else %}
No evidence items registered.
{% endif %}

---

*Report generated by [AutoBug AI](https://github.com/autobug) — Autonomous Bug Detection & Resolution Platform*
"""


def _build_pipeline_status(state: AutoBugState) -> tuple[list, dict]:
    """Sprint 6: Build per-agent status table and summary counts."""
    from app.agents.graph import AGENT_SEQUENCE
    all_names = [name for name, _ in AGENT_SEQUENCE]
    completed = set(state.get("steps_completed") or [])
    skipped = set(state.get("steps_skipped") or [])
    failed = set(state.get("steps_failed") or [])

    rows = []
    for name in all_names:
        # Fix 7: report_agent is always "Completed" — it IS executing right now
        if name == "report_agent":
            rows.append((name, "Completed"))
        elif name in completed:
            rows.append((name, "Completed"))
        elif name in failed:
            rows.append((name, "Failed"))
        elif name in skipped:
            rows.append((name, "Skipped"))
        else:
            rows.append((name, "Not Reached"))

    summary = {
        "completed": len(completed),
        "skipped": len(skipped),
        "failed": len(failed),
        "total": len(all_names),
    }
    return rows, summary


def _build_report(state: AutoBugState) -> str:
    """Build the full markdown report using Jinja2 rendering."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    root_cause = state.get("root_cause") or {}
    patch = state.get("patch") or {}
    test_result = state.get("test_result") or {}
    reviewer = state.get("reviewer_feedback") or {}
    static = state.get("static_analysis_result") or {}
    issue = state.get("issue_structured") or {}
    repro = state.get("reproduction_result") or {}
    pr_url = state.get("pr_url", "")
    steps = state.get("steps_completed") or []

    # Sprint 2: single confidence matrix source of truth
    from app.agents.graph import AGENT_SEQUENCE
    matrix = calculate_confidence_matrix(state)
    total_agents = len(AGENT_SEQUENCE)

    # Sprint 6: pipeline status table
    pipeline_status, steps_summary = _build_pipeline_status(state)

    # Format PR section
    pr_section = f"[View Pull Request]({pr_url})" if pr_url else "PR not created (GitHub token required)"

    # Format test status and reason details
    tests_passed = test_result.get("success") or test_result.get("passed", False)
    test_reason = None
    if test_result:
        stdout_str = test_result.get("stdout") or ""
        stderr_str = test_result.get("stderr") or ""
        if "docker" in stderr_str.lower() or "docker" in stdout_str.lower():
            test_status = "Not Executed"
            test_reason = "Docker sandbox environment failed to build or initialize"
        elif "pytest missing" in stderr_str.lower() or "pytest: command" in stderr_str.lower():
            test_status = "Not Executed"
            test_reason = "pytest testing framework is missing in sandbox environment"
        elif not test_result.get("command") or test_result.get("command") == "N/A":
            test_status = "Not Executed"
            test_reason = test_result.get("error") or "Sandbox environment configuration failed"
        else:
            test_status = "PASSED" if tests_passed else "FAILED"
            test_reason = f"Exit Code {test_result.get('exit_code', '1')}" if not tests_passed else "All tests passed successfully"
    else:
        test_status = "Not Executed"
        test_reason = "Pipeline bypassed validation tests"

    # Determine failure classification
    failure_classification = state.get("failure_classification")
    if not failure_classification:
        test_val = state.get("test_validation_result") or {}
        failure_classification = test_val.get("failure_classification")
    if not failure_classification:
        failed_agent = state.get("failed_agent")
        if failed_agent == "environment_validator_agent":
            failure_classification = "ENVIRONMENT"
        elif failed_agent == "build_agent":
            failure_classification = "BUILD"
        elif failed_agent == "test_runner_agent":
            test_res = state.get("test_result") or {}
            out = (test_res.get("stdout") or "") + (test_res.get("stderr") or "")
            if "ModuleNotFoundError" in out or "ImportError" in out:
                failure_classification = "TEST_COLLECTION"
            else:
                failure_classification = "TEST_FAILURE"
        elif failed_agent == "consistency_checker":
            failure_classification = "VALIDATION"
        elif failed_agent:
            failure_classification = "PIPELINE"
        else:
            failure_classification = "APPLICATION"

    # Determine patch correctness & validation blocked reason
    validation_blocked_reason = None
    if failure_classification in ("TEST_GENERATION", "TEST_COLLECTION", "ENVIRONMENT"):
        patch_correctness = "NOT VERIFIED"
        if failure_classification == "ENVIRONMENT":
            validation_blocked_reason = "Validation blocked during environment setup."
        elif failure_classification == "TEST_GENERATION":
            validation_blocked_reason = "Validation blocked due to test syntax / generation error."
        else:
            validation_blocked_reason = "Validation blocked during test collection."
    else:
        patch_correctness = "VERIFIED (PASSED)" if tests_passed else "VERIFIED (FAILED)"

    # Sprint 5: evaluate decision programmatically if the node was bypassed
    from app.agents.decision_engine import _evaluate_decision
    decision = state.get("decision") or _evaluate_decision(state)

    risk = state.get("risk_analysis") or {}
    if "risk_agent" not in steps:
        risk_reasoning = "Risk analysis skipped because validation did not complete."
    else:
        risk_reasoning = risk.get("reasoning") or "No risk analysis reasoning provided."

    # Context variables
    ctx = {
        "now": now,
        "issue_id": state.get("issue_id", "N/A"),
        "repo_url": state.get("repo_url", "N/A"),
        "issue": issue,
        "matrix": matrix,
        "total_agents": total_agents,
        "pipeline_status": pipeline_status,   # Sprint 6
        "steps_summary": steps_summary,        # Sprint 6
        "decision": decision,                  # Sprint 5
        "repro": repro,
        "tests_passed": tests_passed,
        "test_status": test_status,
        "test_reason": test_reason,
        "test_result": test_result,
        "pr_section": pr_section,
        "root_cause": root_cause,
        "patch": patch,
        "static": static,
        "reviewer": reviewer,
        "risk": risk,
        "risk_reasoning": risk_reasoning,
        "failure_classification": failure_classification,
        "patch_correctness": patch_correctness,
        "validation_blocked_reason": validation_blocked_reason,
        "metrics": state.get("metrics") or {
            "node_durations": {},
            "costs": {},
            "total_duration_seconds": 0.0,
            "total_cost": 0.0
        },
        "steps": steps,
        "env_result": state.get("environment_result") or {},          # Fix 7/Env Health
        "evidence_catalog": state.get("evidence_catalog") or {},       # Fix 8
    }

    template = Template(JINJA_TEMPLATE)
    return template.render(ctx)


def _export_html(markdown_text: str, issue_id: str) -> tuple[str, str]:
    """Sprint 10: Convert markdown report to standalone HTML and save to disk."""
    import os
    try:
        import markdown as md_lib
        html_body = md_lib.markdown(markdown_text, extensions=["tables", "fenced_code"])
    except ImportError:
        # Fallback — wrap raw markdown in pre tag if library not installed
        html_body = f"<pre>{markdown_text}</pre>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>AutoBug AI Report — {issue_id}</title>
<style>
  body {{ font-family: Arial, sans-serif; max-width: 960px; margin: 40px auto; padding: 0 20px; color: #222; }}
  h1, h2, h3 {{ color: #1a1a2e; }}
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
  th, td {{ border: 1px solid #ccc; padding: 8px 12px; text-align: left; }}
  th {{ background: #f0f0f0; }}
  pre, code {{ background: #f5f5f5; padding: 4px 8px; border-radius: 4px; overflow-x: auto; }}
  details summary {{ cursor: pointer; font-weight: bold; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    out_dir = "/tmp/autobug_reports"
    os.makedirs(out_dir, exist_ok=True)
    path = f"{out_dir}/report_{issue_id}.html"
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
    except Exception:
        path = ""
    return html, path

