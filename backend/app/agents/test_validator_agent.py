"""
AutoBug AI — Test Validator Agent
==================================
Validates syntax and imports of generated regression tests before execution.
"""

from __future__ import annotations

import logging

from app.agents.state import AutoBugState
from app.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)


async def test_validator_agent(state: AutoBugState) -> AutoBugState:
    """Validate generated test files for imports and compilation errors."""
    logger.info("[TestValidatorAgent] Validating generated tests")
    try:
        tests = state.get("generated_tests") or {}
        runtime = state.get("runtime_info") or {}
        repo_path = state.get("repo_path", "")
        language = runtime.get("language", "Python")

        test_file = tests.get("test_file", "tests/test_regression.py")

        manager = SandboxManager()
        session = await manager.create_session(repo_path, job_id=state.get("job_id"))

        # Check if file exists first
        check_exist = await manager.run_command(session, f"ls /repo/{test_file}", timeout=10)
        if check_exist.exit_code != 0:
            return {
                **state,
                "test_validation_result": {
                    "valid": False,
                    "error": f"Test file not found: {test_file}",
                    "failure_classification": "TEST_GENERATION",
                },
                "steps_completed": [*(state.get("steps_completed") or []), "test_validator_agent"],
            }

        valid = True
        err_msg = ""
        failure_class = "TEST_GENERATION"

        if language == "Python":
            # 1. Syntax Check
            syntax_check = await manager.run_command(
                session, f"python3 -m py_compile /repo/{test_file}", timeout=20
            )
            if syntax_check.exit_code != 0:
                valid = False
                err_msg = f"Syntax Error: {syntax_check.stderr or syntax_check.stdout}"
                failure_class = "TEST_GENERATION"
            else:
                # 2. Import Resolve Check
                mod_name = test_file.replace("/", ".").replace(".py", "")
                import_check = await manager.run_command(
                    session,
                    f"python3 -c \"import sys; sys.path.insert(0, '/repo'); import {mod_name}\"",
                    timeout=30,
                )
                if import_check.exit_code != 0:
                    valid = False
                    err_msg = f"Import Error: {import_check.stderr or import_check.stdout}"
                    if "ModuleNotFoundError" in err_msg or "ImportError" in err_msg:
                        failure_class = "TEST_COLLECTION"
                    else:
                        failure_class = "TEST_GENERATION"

        elif language in ("JavaScript", "TypeScript"):
            check = await manager.run_command(
                session, f"node --check /repo/{test_file}", timeout=20
            )
            if check.exit_code != 0:
                valid = False
                err_msg = f"Syntax/Import Error: {check.stderr or check.stdout}"
                failure_class = "TEST_GENERATION"

        logger.info(
            "[TestValidatorAgent] Validation Result: %s, Class: %s",
            "VALID" if valid else "INVALID",
            failure_class if not valid else "N/A",
        )

        return {
            **state,
            "test_validation_result": {
                "valid": valid,
                "error": err_msg if not valid else None,
                "failure_classification": failure_class if not valid else None,
            },
            "steps_completed": [*(state.get("steps_completed") or []), "test_validator_agent"],
        }
    except Exception as exc:
        logger.error("[TestValidatorAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "test_validation_result": {
                "valid": False,
                "error": f"Validator exception: {str(exc)}",
                "failure_classification": "PIPELINE",
            },
            "steps_completed": [*(state.get("steps_completed") or []), "test_validator_agent"],
        }
