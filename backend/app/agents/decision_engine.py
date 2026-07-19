"""
AutoBug AI — Decision Engine  (Sprint 5)
==========================================
Programmatic merge/ship decision rules.
No LLM calls — pure state evaluation.
"""

from __future__ import annotations

import logging

from app.agents.state import AutoBugState

logger = logging.getLogger(__name__)


def _evaluate_decision(state: AutoBugState) -> dict:
    """Apply deterministic decision rules and return a DecisionResult dict (Fix 10)."""
    from app.core.confidence import calculate_confidence_matrix

    matrix = calculate_confidence_matrix(state)
    overall_conf = matrix["overall_release_confidence"] * 100

    env_result = state.get("environment_result") or {}
    env_ready = env_result.get("ready", True)

    risk = state.get("risk_analysis") or {}
    regression_risk = risk.get("regression_risk", 0.0)
    risk_level = risk.get("risk_level", "low").lower()

    validation = state.get("validation_result") or {}
    tests_executed = validation.get("tests_executed", False)
    tests_passed = validation.get("tests_passed", False)

    test_result = state.get("test_result") or {}
    tests_passed = tests_passed or test_result.get("success") or test_result.get("passed", False)
    tests_executed = tests_executed or bool(test_result.get("command") and test_result.get("command") != "N/A")

    reviewer = state.get("reviewer_feedback") or {}
    reviewer_approved = reviewer.get("approved", False)

    blocking_factors: list[str] = []
    decision: str
    reason: str
    next_steps: list[str]

    # Rule 0: Environment not ready → blocked (no analysis is trustworthy)
    if not env_ready:
        missing = env_result.get("still_missing") or []
        decision = "BLOCKED"
        reason = "Validation environment unavailable"
        blocking_factors.append(f"Missing tools: {', '.join(missing) if missing else 'unknown'}")
        next_steps = [
            f"Install missing tools: {', '.join(missing) if missing else 'pytest, git'}",
            "Retry validation",
            "Re-run the environment_validator_agent to confirm readiness",
            "Consider updating the Docker image to pre-install required tools",
        ]

    # Rule 1: tests ran and failed → changes required
    elif tests_executed and not tests_passed:
        decision = "Changes Required"
        reason = "Validation tests failed — patch must pass all tests before merge."
        blocking_factors.append("Tests failed")
        next_steps = [
            "Review failing test output in the Validation section below",
            "Fix the root cause of failing assertions in the generated patch",
            "Re-run tests locally: check test_result.command in this report",
            "Re-submit patch once all tests pass",
        ]

    # Rule 2: tests not executed → manual review
    elif not tests_executed:
        failed_reason = validation.get("failed_reason") or "Tests could not be executed"
        decision = "Manual Review Required"
        reason = f"Validation tests not executed: {failed_reason}"
        blocking_factors.append("Tests not executed")
        next_steps = [
            "Verify the sandbox environment is ready (see Pipeline Status table)",
            "Check environment_validator_agent tool results for missing tools",
            "Install any missing test framework tools",
            "Re-trigger the validation step manually",
        ]

    # Rule 3: static analysis failures are a hard validation gate.
    elif not (state.get("static_analysis_result") or {}).get("passed", True):
        decision = "Changes Required"
        reason = "Static analysis failed — resolve blocking analysis errors before merge."
        blocking_factors.append("Static analysis failed")
        next_steps = ["Fix static-analysis errors", "Re-run validation", "Re-submit the patch once validation passes"]

    # Rule 4: high regression risk → reject
    elif regression_risk >= 0.7 or risk_level == "high":
        decision = "Reject"
        reason = f"High regression risk ({regression_risk * 100:.0f}%) — patch requires re-evaluation."
        blocking_factors.append("High regression risk")
        next_steps = [
            "Review the Risk Analysis section for specific regression concerns",
            "Narrow the patch scope to reduce regression surface area",
            "Add targeted regression tests for the affected code paths",
            "Re-submit the patch with a smaller, more focused change",
        ]

    # Rule 4: low overall confidence → needs review
    elif overall_conf < 70:
        decision = "Needs Review"
        reason = f"Overall release confidence ({overall_conf:.0f}%) is below the 70% threshold."
        blocking_factors.append("Low confidence score")
        next_steps = [
            "Review the Confidence Breakdown section to identify which checks failed",
            "Run reproduction steps manually to generate runtime evidence",
            "Ensure validation tests execute successfully",
            "Address any reviewer blocking issues before re-evaluation",
        ]

    # Rule 5: reviewer rejected → needs review
    elif not reviewer_approved:
        decision = "Needs Review"
        reason = "Code reviewer did not approve the patch — address reviewer feedback."
        blocking_factors.append("Reviewer did not approve")
        next_steps = [
            "Review blocking issues listed in the Code Review section",
            "Address each blocking issue in the patch",
            "Re-submit the patch for reviewer re-evaluation",
        ]

    # Rule 6: all checks pass → ready for merge
    else:
        decision = "Ready for Merge"
        reason = (
            f"All checks passed: tests passed, confidence {overall_conf:.0f}%, "
            f"risk level {risk_level}, reviewer approved."
        )
        next_steps = [
            "Approve the pull request linked in the Executive Summary",
            "Merge to main branch using squash merge to keep history clean",
            "Monitor post-merge for any runtime regressions",
            "Close the original issue once the fix is verified in production",
        ]

    allow_commit = (decision == "Ready for Merge")
    allow_pr = (decision == "Ready for Merge")
    status = "ready_for_merge" if allow_commit else decision.lower().replace(" ", "_").replace(":", "")

    return {
        "decision": decision,
        "status": status,
        "reason": reason,
        "blocking_factors": blocking_factors,
        "next_steps": next_steps,
        "overall_confidence": round(overall_conf, 1),
        "regression_risk_pct": round(regression_risk * 100, 1),
        "allow_commit": allow_commit,
        "allow_pr": allow_pr,
        "allow_report": True,
        "allow_retry": not allow_commit,
    }


async def decision_engine(state: AutoBugState) -> AutoBugState:
    """Run decision rules and populate state['decision']."""
    logger.info("[DecisionEngine] Evaluating merge decision")
    try:
        result = _evaluate_decision(state)
        logger.info("[DecisionEngine] Decision: %s — %s", result["decision"], result["reason"])
        return {
            **state,
            "decision": result,
            "steps_completed": [*(state.get("steps_completed") or []), "decision_engine"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[DecisionEngine] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "decision": {
                "decision": "Manual Review",
                "status": "manual_review",
                "reason": f"Decision engine error: {exc}",
                "blocking_factors": ["Decision engine crashed"],
                "allow_commit": False,
                "allow_pr": False,
                "allow_report": True,
                "allow_retry": True,
            },
            "steps_completed": [*(state.get("steps_completed") or []), "decision_engine"],
        }
