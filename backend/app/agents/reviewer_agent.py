"""
AutoBug AI — Reviewer Agent  (Sprint 4)
=========================================
Evidence-only LLM code review. Every claim must reference concrete
evidence from sandbox execution logs, static analysis, or test results.
"""

from __future__ import annotations

import json
import logging

from app.agents.issue_agent import _extract_json, _get_llm
from app.agents.state import AutoBugState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior code reviewer producing an auditable engineering review.

CRITICAL RULES — violating these invalidates the review:
1. Do NOT speculate. Every claim you make must be supported by the evidence provided (static analysis results, test logs, execution output).
2. Do NOT invent syntax errors. If the static analysis linter did not report an error, there is no syntax error.
3. Do NOT flag valid JavaScript async DOM event handlers as bugs. `element.addEventListener("event", asyncFn)` is perfectly valid — the browser does not await event handlers.
4. Do NOT say "Verified" or "Approved" if tests failed or were not executed.
5. If validation failed, state clearly: "Correctness cannot be fully verified — tests did not pass."
6. Reference evidence by ID (e.g. EV-001) when available.
7. Only review the diff lines — lines prefixed '+' are additions, '-' are deletions.

Scoring Guidelines:
- 8.5–10.0: Correct fix, clean logic, tests pass, no open issues.
- 7.0–8.4: Correct fix, tests pass, minor style or redundant code.
- 5.0–6.9: Fix may work but introduces risk, tests failed or unverified.
- Below 5.0: Tests failed + critical logic error, or deletion of working code.

Return ONLY a JSON object:
{
  "approved": false,
  "recommendation": "approved | reject | request_changes",
  "overall_score": 7.5,
  "correctness_score": 8.0,
  "security_score": 9.0,
  "quality_score": 7.5,
  "confidence": 0.75,
  "strengths": ["What the patch does well, referencing diff lines or evidence."],
  "weaknesses": ["Honest weaknesses based only on evidence — not speculation."],
  "blocking_issues": ["Issues that MUST be fixed before merge. Empty list if none."],
  "comments": ["General review comments."],
  "critical_issues": ["Critical issues only — syntax errors proven by linter, deletion of active code. Empty list if none."],
  "suggestions": ["Non-blocking improvement suggestions."],
  "evidence_refs": ["EV-001", "EV-003"]
}
"""


async def _apply_rule_phase(review: dict, state: AutoBugState) -> dict:
    """
    Fix 3 — Phase 2: Rule engine hard-overrides LLM opinion with objective facts.
    This runs AFTER the LLM review and is not negotiable.
    """
    env = state.get("environment_result") or {}
    test_result = state.get("test_result") or {}
    validation = state.get("validation_result") or {}

    tests_passed   = test_result.get("success") or test_result.get("passed", False)
    tests_executed = bool(test_result.get("command") and test_result.get("command") != "N/A")
    env_ready      = env.get("ready", True)

    blocking = list(review.get("blocking_issues") or [])
    comments = list(review.get("comments") or [])

    # Rule A: Environment not ready — nothing can be verified
    if not env_ready:
        reason = env.get("blocking_reason", "Environment not ready")
        blocking.insert(0, f"Environment not ready: {reason}. Correctness cannot be verified without a working sandbox.")
        review["approved"] = False
        review["recommendation"] = "request_changes"
        review["confidence"] = min(review.get("confidence", 0.5), 0.30)
        review["correctness_score"] = min(review.get("correctness_score", 5.0), 4.0)
        comments.insert(0, "Phase-2 Rule A: Logic may appear correct, but correctness is unverifiable — validation environment was not ready. Manual review required.")

    # Rule B: Tests not executed — correctness unverifiable
    elif not tests_executed:
        blocking.insert(0, "Validation not executed — correctness cannot be confirmed. Environment may need setup.")
        review["approved"] = False
        review["recommendation"] = "request_changes"
        review["confidence"] = min(review.get("confidence", 0.5), 0.40)
        comments.insert(0, "Phase-2 Rule B: Logic appears structurally correct based on static analysis, but correctness cannot be fully verified — validation tests were not executed. Manual review required before merge.")

    # Rule C: Tests ran but failed — reject
    elif not tests_passed:
        blocking.insert(0, "Validation tests failed — patch does not pass existing test suite.")
        review["approved"] = False
        review["recommendation"] = "reject"
        review["confidence"] = min(review.get("confidence", 0.5), 0.35)
        comments.insert(0, "Phase-2 Rule C: Patch did not pass validation tests. Correctness is not verified. Changes required before merge.")

    review["blocking_issues"] = blocking
    review["comments"] = comments
    return review


async def reviewer_agent(state: AutoBugState) -> AutoBugState:
    """Perform evidence-only LLM code review of the patch."""
    logger.info("[ReviewerAgent] Running evidence-only review")
    try:
        patch = state.get("patch") or {}
        tests = state.get("generated_tests") or {}
        test_result = state.get("test_result") or {}
        root_cause = state.get("root_cause") or {}
        static = state.get("static_analysis_result") or {}
        validation = state.get("validation_result") or {}
        evidence_catalog = state.get("evidence_catalog") or {}

        # Build evidence summary for context
        evidence_summary = "\n".join(
            f"  {eid}: [{item.get('kind', 'unknown')}] {item.get('description', '')}"
            for eid, item in evidence_catalog.items()
        ) or "  No structured evidence collected."

        tests_passed = test_result.get("success") or test_result.get("passed", False)
        tests_executed = validation.get("tests_executed", bool(test_result.get("command")))
        static_passed = static.get("passed", True)
        static_issues = static.get("issues") or []

        llm = _get_llm("reviewer_agent")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""
Root Cause:
{json.dumps(root_cause, indent=2)}

Generated Patch (unified diff):
{patch.get("unified_diff", "No patch")}

Patch Summary: {patch.get("patch_summary", "")}

--- EVIDENCE ---
{evidence_summary}

--- STATIC ANALYSIS ---
Passed: {static_passed}
Issues reported by linter: {json.dumps(static_issues[:10], indent=2)}

--- VALIDATION RESULTS ---
Tests executed: {tests_executed}
Tests passed: {tests_passed}
Test exit code: {test_result.get("exit_code", "N/A")}
Test stdout (last 1000 chars):
{str(test_result.get("stdout", ""))[-1000:]}
Test stderr (last 500 chars):
{str(test_result.get("stderr", ""))[-500:]}

--- GENERATED TESTS ---
{tests.get("test_code", "No tests generated")}
"""},
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        review = _extract_json(content)

        # Phase 1 complete. Now run Phase 2 (rule engine).
        review = await _apply_rule_phase(review, state)

        # If no blocking issues found by either phase, LLM review stands as approved
        if not review.get("blocking_issues") and not review.get("critical_issues"):
            review["approved"] = True
            review["recommendation"] = "approved"

        logger.info("[ReviewerAgent] approved=%s score=%s recommendation=%s",
                    review.get("approved"), review.get("overall_score"), review.get("recommendation"))

        return {
            **state,
            "reviewer_feedback": review,
            "steps_completed": [*(state.get("steps_completed") or []), "reviewer_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[ReviewerAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "reviewer_feedback": {
                "approved": False,
                "recommendation": "request_changes",
                "overall_score": 6.0,
                "comments": [f"Reviewer agent crashed: {exc}"],
                "critical_issues": [],
                "strengths": [],
                "weaknesses": [],
                "blocking_issues": [],
            },
            "steps_completed": [*(state.get("steps_completed") or []), "reviewer_agent"],
        }

