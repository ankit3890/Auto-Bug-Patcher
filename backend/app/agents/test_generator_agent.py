"""
AutoBug AI — Test Generator Agent
====================================
Generates regression and unit tests for the bug fix using LLM.
"""

from __future__ import annotations

import json
import logging

from app.agents.issue_agent import _extract_json, _get_llm
from app.agents.state import AutoBugState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior software engineer writing tests for a bug fix.
Generate a regression test that:
1. Reproduces the bug (fails without the fix)
2. Verifies the fix works (passes with the fix)
3. Covers edge cases related to the bug

Return ONLY a JSON object:
{
  "test_code": "import pytest\\n\\ndef test_bug_regression():\\n    ...",
  "test_file": "tests/test_bug_ISSUE_ID.py",
  "test_framework": "pytest|jest|go_test|...",
  "description": "What these tests verify"
}
"""


async def test_generator_agent(state: AutoBugState) -> AutoBugState:
    """Generate regression and unit tests."""
    logger.info("[TestGeneratorAgent] Generating tests")
    try:
        root_cause = state.get("root_cause") or {}
        patch = state.get("patch") or {}
        issue = state.get("issue_structured") or {}
        runtime = state.get("runtime_info") or {}
        issue_id = state.get("issue_id", "unknown")
        retries = state.get("test_gen_retries") or 0

        # Check for previous validation error
        val_res = state.get("test_validation_result") or {}
        val_error = val_res.get("error")
        feedback_str = ""
        if val_error:
            retries += 1
            feedback_str = (
                f"\n\nCRITICAL FEEDBACK (Attempt {retries}):\n"
                f"Your previous test failed validation during syntax check or import resolve with the following error:\n"
                f"{val_error}\n"
                f"Please correct the imports (make sure you do NOT import modules that do not exist, e.g., 'public' or 'api', "
                f"unless they are local files present in the repo) and ensure the syntax compiles perfectly."
            )

        llm = _get_llm("test_generator_agent")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.replace("ISSUE_ID", issue_id[:8])},
            {"role": "user", "content": f"""
Root Cause:
{json.dumps(root_cause, indent=2)}

Applied Patch:
{json.dumps(patch, indent=2)}

Bug Description:
{json.dumps(issue, indent=2)}

Runtime: {runtime.get("language", "Python")}{feedback_str}
"""},
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        test_data = _extract_json(content)

        logger.info("[TestGeneratorAgent] Generated %s", test_data.get("test_file", "tests"))
        return {
            **state,
            "generated_tests": test_data,
            "test_gen_retries": retries,
            "steps_completed": [*(state.get("steps_completed") or []), "test_generator_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[TestGeneratorAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "generated_tests": {"test_code": "", "test_file": "tests/test_regression.py"},
            "steps_completed": [*(state.get("steps_completed") or []), "test_generator_agent"],
        }
