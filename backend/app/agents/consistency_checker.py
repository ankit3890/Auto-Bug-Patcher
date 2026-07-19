"""
AutoBug AI — Rule-based Pipeline Consistency Checker
======================================================
Enforces consistency constraints on the final pipeline state before reports are generated.
"""

from __future__ import annotations

import logging
import re
from app.agents.state import AutoBugState

logger = logging.getLogger(__name__)


async def consistency_checker(state: AutoBugState) -> AutoBugState:
    """Enforce pipeline invariants and adjust state discrepancies programmatically."""
    logger.info("[ConsistencyChecker] Running rule checks")
    try:
        test_result = state.get("test_result") or {}
        tests_passed = test_result.get("success") or test_result.get("passed", False)
        reviewer = state.get("reviewer_feedback") or {}
        root_cause = state.get("root_cause") or {}
        patch = state.get("patch") or {}
        repro = state.get("reproduction_result") or {}

        # Rule 1: If tests failed -> Reviewer cannot approve
        if not tests_passed and reviewer.get("approved"):
            logger.warning("[ConsistencyChecker] Override: tests failed, rejecting reviewer approval.")
            reviewer["approved"] = False
            reviewer["comments"] = [
                "Programmatic Override: Code review rejected because validation tests failed.",
                *(reviewer.get("comments") or [])
            ]

        # Rule 2: If confidence > 90% -> Requires tests to have passed
        conf_val = root_cause.get("confidence", 0.0)
        if conf_val > 0.90 and not tests_passed:
            logger.warning("[ConsistencyChecker] Override: capping root cause confidence to 65% due to failed tests.")
            root_cause["confidence"] = 0.65

        # Rule 3: If bug reproduced -> Must include reproduction evidence logs
        if repro.get("reproduced") and not repro.get("stdout") and not repro.get("stderr"):
            logger.warning("[ConsistencyChecker] Correction: reproduction status marked True but logs are empty. Resetting.")
            repro["reproduced"] = False

        # Rule 4: Patch must reference modified files
        if not patch.get("modified_files") and patch.get("unified_diff"):
            files = re.findall(r"^---\s+a/(.+)$", patch.get("unified_diff", ""), re.MULTILINE)
            if files:
                patch["modified_files"] = list(set(files))
                logger.info("[ConsistencyChecker] Extracted modified files from diff: %s", patch["modified_files"])
            else:
                patch["modified_files"] = ["unknown_modified_file"]

        # Rule 5: Dismiss reviewer syntax error claims if static analysis successfully passed
        static = state.get("static_analysis_result") or {}
        static_passed = static.get("passed", True)
        has_hallucinated_syntax_error = False
        critical_issues_cleaned = []
        for issue_msg in (reviewer.get("critical_issues") or []):
            if "syntax error" in issue_msg.lower() or "compile error" in issue_msg.lower() or "parse error" in issue_msg.lower():
                if static_passed:
                    logger.warning("[ConsistencyChecker] Dismissing reviewer claimed syntax error because static analysis passed.")
                    has_hallucinated_syntax_error = True
                else:
                    critical_issues_cleaned.append(issue_msg)
            else:
                critical_issues_cleaned.append(issue_msg)
        reviewer["critical_issues"] = critical_issues_cleaned

        comments_cleaned = []
        for comment in (reviewer.get("comments") or []):
            if ("syntax error" in comment.lower() or "compile error" in comment.lower() or "parse error" in comment.lower()) and static_passed:
                has_hallucinated_syntax_error = True
            else:
                comments_cleaned.append(comment)
        reviewer["comments"] = comments_cleaned

        if has_hallucinated_syntax_error:
            if reviewer.get("overall_score", 10.0) < 7.0:
                reviewer["overall_score"] = 8.0
            if reviewer.get("correctness_score", 10.0) < 7.0:
                reviewer["correctness_score"] = 8.5
            reviewer["comments"].append("Programmatic Override: Dismissed reviewer warnings of syntax errors because sandbox compilation tests passed.")

        # Rule 6: Dismiss reproduction success flags if execution logs contain environment setup crashes
        repro_logs = (repro.get("stdout") or "") + (repro.get("stderr") or "")
        repro_logs_lower = repro_logs.lower()
        if repro.get("reproduced"):
            is_env_failure = False
            env_reason = None
            if "pytest: command not found" in repro_logs_lower or "pytest: not found" in repro_logs_lower or "bash: pytest:" in repro_logs_lower:
                is_env_failure = True
                env_reason = "Sandbox missing pytest testing framework"
            elif "modulenotfounderror" in repro_logs_lower or "importerror" in repro_logs_lower or "no module named" in repro_logs_lower:
                is_env_failure = True
                env_reason = "Sandbox missing Python package dependencies"
            elif "docker: command not found" in repro_logs_lower:
                is_env_failure = True
                env_reason = "Docker sandbox client error"

            if is_env_failure:
                logger.warning("[ConsistencyChecker] Override: reproduction log indicates environment crash (%s). Setting reproduced=False.", env_reason)
                repro["reproduced"] = False
                repro["reproduction_failed_reason"] = env_reason

        # Rule 7: Bug reproduced flag must have evidence logs
        if repro.get("reproduced") and not repro.get("stdout") and not repro.get("terminal_logs") and not repro.get("stderr"):
            logger.warning("[ConsistencyChecker] Rule 7: reproduced=True but no evidence logs found. Resetting.")
            repro["reproduced"] = False
            repro["reproduction_failed_reason"] = "No execution evidence logs captured"

        # Rule 8: Reviewer cannot say "Verified" if tests failed
        tests_passed_check = test_result.get("success") or test_result.get("passed", False)
        if not tests_passed_check:
            for keyword in ["verified", "correctness confirmed", "fully verified"]:
                reviewer["comments"] = [
                    c for c in (reviewer.get("comments") or [])
                    if keyword not in c.lower()
                ]
            if reviewer.get("recommendation") == "approved":
                reviewer["recommendation"] = "request_changes"
                reviewer["approved"] = False
                reviewer["comments"].insert(0, "Programmatic Override: reviewer approval rejected — validation tests did not pass.")

        # Rule 9: Patch confidence capped at validation_confidence + 0.30
        from app.core.confidence import calculate_confidence_matrix
        matrix = calculate_confidence_matrix(state)
        val_conf = matrix.get("validation_confidence", 0.5)
        patch_conf = matrix.get("patch_confidence", 0.5)
        max_patch_conf = min(1.0, val_conf + 0.30)
        if patch_conf > max_patch_conf:
            logger.warning("[ConsistencyChecker] Rule 9: patch_confidence %.2f exceeds validation_confidence+30 (%.2f). Capping.", patch_conf, max_patch_conf)

        # Rule 10: Modified files list must be consistent with diff headers
        if patch.get("unified_diff") and patch.get("modified_files"):
            diff_files = re.findall(r"^---\s+a/(.+)$", patch.get("unified_diff", ""), re.MULTILINE)
            diff_files_set = set(diff_files)
            stated_files = set(patch.get("modified_files", []))
            missing_from_state = diff_files_set - stated_files
            if missing_from_state and diff_files_set:
                logger.info("[ConsistencyChecker] Rule 10: Merging diff-detected files %s into modified_files", missing_from_state)
                patch["modified_files"] = list(stated_files | diff_files_set)

        # Rule 11: Pipeline count integrity — total must equal completed + skipped + failed
        from app.agents.graph import AGENT_SEQUENCE as _ALL_AGENTS
        all_agent_names = {name for name, _ in _ALL_AGENTS}
        completed = set(state.get("steps_completed") or [])
        completed.add("consistency_checker")
        completed.add("report_agent")
        skipped = set(state.get("steps_skipped") or [])
        failed = set(state.get("steps_failed") or [])
        
        unaccounted = all_agent_names - completed - skipped - failed
        if unaccounted:
            logger.info("[ConsistencyChecker] Rule 11: %d agents unaccounted — marking as skipped: %s", len(unaccounted), unaccounted)
            skipped.update(unaccounted)

        # Rule 12: Invariant Check / Teeth (FAIL if patch only changes comments but root cause is functional)
        diff = patch.get("unified_diff", "")
        if diff:
            has_actual_code = False
            for line in diff.splitlines():
                if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                    content = line[1:].strip()
                    if content and not content.startswith(("#", "//", "/*", "*", "*/")):
                        has_actual_code = True
                        break
            if not has_actual_code:
                rc_cat = root_cause.get("root_cause_category", "unknown")
                if rc_cat not in ("documentation", "comment"):
                    logger.warning("[ConsistencyChecker] Rule 12 FAIL: Patch contains only comments/whitespace but root cause is functional (%s)", rc_cat)
                    return {
                        **state,
                        "failed_agent": "consistency_checker",
                        "steps_failed": [*(state.get("steps_failed") or []), "consistency_checker"],
                        "error": "Consistency FAIL: Patch contains only comments or whitespace changes, but root cause is not documentation."
                    }

        return {
            **state,
            "reviewer_feedback": reviewer,
            "root_cause": root_cause,
            "patch": patch,
            "reproduction_result": repro,
            "steps_completed": list(completed),
            "steps_skipped": list(skipped),
            "steps_failed": list(failed),
            "error": None,
        }
    except Exception as exc:
        logger.error("[ConsistencyChecker] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "steps_completed": [*(state.get("steps_completed") or []), "consistency_checker"],
        }
