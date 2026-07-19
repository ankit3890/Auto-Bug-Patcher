"""
AutoBug AI — Programmatic Confidence Engine  (Fix 4 + Fix 9)
=============================================================
Calculates pipeline confidence scores programmatically from concrete evidence.
Applies hard caps based on reproduction and validation tiers (Fix 4).
Returns human-readable confidence_explanation checklist (Fix 9).
"""

from __future__ import annotations

from typing import Any, Mapping


# ── Fix 4: Evidence tiers define hard caps on root_cause_confidence ──────────

def _root_cause_cap(repro: dict, test_result: dict, state: Mapping[str, Any] = None) -> tuple[float, str]:
    """
    Return (cap, tier_label) based on what evidence is available.

    Tier A: Reproduced + tests passed              → max 0.95
    Tier B: Reproduced + tests failed/not run       → max 0.75
    Tier C: Not reproduced + static evidence        → max 0.65
    Tier D: Not reproduced + no static evidence     → max 0.40
    Tier E: Validation Blocked (env/tests invalid)  → max 0.35
    """
    if state:
        failure_class = state.get("failure_classification")
        if not failure_class:
            test_val = state.get("test_validation_result") or {}
            failure_class = test_val.get("failure_classification")
        if failure_class in ("TEST_GENERATION", "TEST_COLLECTION", "ENVIRONMENT"):
            return 0.35, f"Tier E (Validation Blocked — {failure_class})"

    reproduced = repro.get("reproduced", False)
    tests_passed = test_result.get("success") or test_result.get("passed", False)
    tests_executed = bool(test_result.get("command") and test_result.get("command") != "N/A")

    if reproduced and tests_passed:
        return 0.95, "Tier A (Reproduced + Tests Passed)"
    if reproduced:
        return 0.75, "Tier B (Reproduced, Tests Unavailable)"
    if test_result:  # some static evidence exists
        return 0.65, "Tier C (Not Reproduced, Static Evidence Only)"
    return 0.40, "Tier D (Not Reproduced, No Static Evidence)"


# ── Fix 9: Human-readable confidence explanation ──────────────────────────────

def _build_explanation(
    repro: dict,
    test_result: dict,
    static: dict,
    reviewer: dict,
    patch: dict,
    tier_label: str,
    state: Mapping[str, Any] = None,
) -> list[str]:
    """Build a checklist of PASS/FAIL items explaining the confidence score."""
    items = []

    if state:
        failure_class = state.get("failure_classification")
        if not failure_class:
            test_val = state.get("test_validation_result") or {}
            failure_class = test_val.get("failure_classification")
        if failure_class in ("TEST_GENERATION", "TEST_COLLECTION", "ENVIRONMENT"):
            items.append(f"BLOCK Validation blocked due to {failure_class} error (-40 pts)")

    # Reproduction
    if repro.get("reproduced"):
        items.append("PASS  Bug reproduced in sandbox (+25 pts)")
    else:
        reason = repro.get("reproduction_failed_reason") or "reason unknown"
        items.append(f"FAIL  Runtime reproduction unavailable — {reason} (-25 pts)")

    # Static analysis
    static_passed = static.get("passed", True)
    static_skipped = static.get("skipped", False)
    if static_skipped:
        items.append("SKIP  Static analysis skipped (no patch to analyse)")
    elif static_passed:
        items.append("PASS  Static analysis passed — no lint errors detected (+20 pts)")
    else:
        n = len(static.get("issues") or [])
        items.append(f"FAIL  Static analysis found {n} issue(s) (-10 pts)")

    # Patch size
    diff = patch.get("unified_diff") or ""
    diff_lines = len([l for l in diff.splitlines() if l.startswith(("+", "-")) and not l.startswith(("---", "+++"))])
    if 0 < diff_lines <= 50:
        items.append(f"PASS  Small, focused patch ({diff_lines} changed lines) (+5 pts)")
    elif diff_lines > 50:
        items.append(f"WARN  Large patch ({diff_lines} changed lines) — higher regression risk")
    else:
        items.append("SKIP  No patch generated")

    # Tests
    tests_passed = test_result.get("success") or test_result.get("passed", False)
    tests_executed = bool(test_result.get("command") and test_result.get("command") != "N/A")
    if tests_passed:
        items.append("PASS  Validation tests passed — correctness verified (+30 pts)")
    elif tests_executed:
        items.append("FAIL  Validation tests executed but failed (-20 pts)")
    else:
        items.append("FAIL  Validation tests not executed — correctness unverifiable (-30 pts)")

    # Reviewer
    reviewer_approved = reviewer.get("approved", False)
    if reviewer_approved:
        items.append("PASS  Code reviewer approved (+10 pts)")
    else:
        items.append("FAIL  Code reviewer did not approve (-10 pts)")

    # Cap note
    items.append(f"NOTE  Confidence capped at {tier_label}")

    return items


def calculate_confidence(state: Mapping[str, Any]) -> float:
    """
    Simple scalar confidence score (0.0–1.0) for backward compatibility.
    Applications should prefer calculate_confidence_matrix().
    """
    matrix = calculate_confidence_matrix(state)
    return matrix["overall_release_confidence"]


def calculate_confidence_matrix(state: Mapping[str, Any]) -> dict[str, Any]:
    """Calculate multi-dimensional confidence scores, caps, and explanation."""
    root_cause = state.get("root_cause") or {}
    patch = state.get("patch") or {}
    test_result = state.get("test_result") or {}
    reviewer = state.get("reviewer_feedback") or {}
    static = state.get("static_analysis_result") or {}
    issue = state.get("issue_structured") or {}
    repro = state.get("reproduction_result") or {}
    env_result = state.get("environment_result") or {}

    # ── Root Cause Confidence ────────────────────────────────────────────────
    has_loc  = bool(root_cause.get("fault_file"))
    has_line = bool(root_cause.get("fault_line"))
    has_trace = bool(issue.get("stack_trace") or issue.get("error_message"))

    if has_loc and has_line and has_trace:
        rc_base = 0.85
    elif has_loc and has_line:
        rc_base = 0.65
    elif has_loc:
        rc_base = 0.50
    else:
        rc_base = 0.20

    # Fix 4: Apply hard cap based on evidence tier
    cap, tier_label = _root_cause_cap(repro, test_result, state)
    rc_conf = min(rc_base, cap)

    # ── Patch Confidence ────────────────────────────────────────────────────
    static_passed = static.get("passed", True)
    reviewer_approved = reviewer.get("approved", False)
    tests_passed = test_result.get("success") or test_result.get("passed", False)

    if static_passed and reviewer_approved and tests_passed:
        patch_conf = 0.90
    elif static_passed and reviewer_approved:
        patch_conf = 0.70
    elif reviewer_approved:
        patch_conf = 0.60
    elif patch.get("unified_diff"):
        patch_conf = 0.45
    else:
        patch_conf = 0.20

    # ── Validation Confidence ────────────────────────────────────────────────
    test_executed = bool(test_result.get("command") and test_result.get("command") != "N/A")
    env_ready = env_result.get("ready", True)  # assume ready if no env_result

    if not env_ready:
        # Environment blocked — validation confidence is zero
        val_conf = 0.0
    elif tests_passed:
        val_conf = 0.95
    elif test_executed:
        val_conf = 0.55
    else:
        val_conf = 0.15

    # ── Overall Release Confidence ────────────────────────────────────────────
    overall_conf = (rc_conf * 0.30) + (patch_conf * 0.40) + (val_conf * 0.30)

    # ── Evidence Quality Labels ───────────────────────────────────────────────
    static_quality = (
        "Skipped" if static.get("skipped")
        else "Passed" if static_passed
        else "Failed"
    )
    if repro.get("reproduced"):
        repro_quality = "Reproduced"
    elif repro.get("reproduction_failed_reason"):
        repro_quality = f"Error: {repro.get('reproduction_failed_reason')}"
    else:
        repro_quality = "Not Reproduced"

    if tests_passed:
        tests_quality = "Passed"
    elif test_executed:
        tests_quality = "Failed"
    else:
        tests_quality = "Not Executed"

    source_quality = "Passed" if has_loc else "Failed"

    if static_passed and reviewer_approved:
        patch_quality = "Verified"
    elif static_passed or reviewer_approved:
        patch_quality = "Partial"
    else:
        patch_quality = "Rejected"

    # ── Fix 9: Confidence explanation checklist ───────────────────────────────
    explanation = _build_explanation(repro, test_result, static, reviewer, patch, tier_label, state)

    return {
        "root_cause_confidence":      rc_conf,
        "patch_confidence":           patch_conf,
        "validation_confidence":      val_conf,
        "overall_release_confidence": overall_conf,
        "confidence_tier":            tier_label,
        "confidence_explanation":     explanation,   # Fix 9
        "evidence_quality": {
            "static_analysis":        static_quality,
            "runtime_reproduction":   repro_quality,
            "unit_tests":             tests_quality,
            "source_code_analysis":   source_quality,
            "patch_validation":       patch_quality,
        }
    }

