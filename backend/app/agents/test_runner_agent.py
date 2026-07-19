"""
AutoBug AI — Test Runner Agent
================================
Executes generated tests inside the sandbox after applying the patch.
"""

from __future__ import annotations

import logging

from app.agents.state import AutoBugState
from app.agents.evidence_registry import register as reg_evidence
from app.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)


async def test_runner_agent(state: AutoBugState) -> AutoBugState:
    """Apply patch and run tests in sandbox."""
    logger.info("[TestRunnerAgent] Running tests")
    try:
        patch = state.get("patch") or {}
        tests = state.get("generated_tests") or {}
        runtime = state.get("runtime_info") or {}
        repo_path = state.get("repo_path", "")
        language = runtime.get("language", "Python")

        manager = SandboxManager()
        session = await manager.create_session(repo_path, job_id=state.get("job_id"))

        # Apply patch
        unified_diff = patch.get("unified_diff", "")
        patch_applied = False
        if unified_diff:
            await manager.copy_file_to_sandbox(session, unified_diff, "/tmp/fix.patch")
            apply_result = await manager.run_command(session, "cd /repo && patch -p1 < /tmp/fix.patch", timeout=30)
            patch_applied = apply_result.success

        # Write test file
        test_code = tests.get("test_code", "")
        test_file = tests.get("test_file", "tests/test_regression.py")
        if test_code:
            await manager.copy_file_to_sandbox(session, test_code, f"/repo/{test_file}")

        # Run tests
        test_cmds = {
            "Python": f"cd /repo && python -m pytest {test_file} -v --tb=short 2>&1",
            "JavaScript": f"cd /repo && npx jest {test_file} --no-coverage 2>&1",
            "TypeScript": f"cd /repo && npx jest {test_file} --no-coverage 2>&1",
            "Go": "cd /repo && go test ./... 2>&1",
            "Rust": "cd /repo && cargo test 2>&1",
        }
        cmd = test_cmds.get(language, f"cd /repo && python -m pytest {test_file} -v 2>&1")
        result = await manager.run_command(session, cmd, timeout=180)

        passed = result.success
        logger.info("[TestRunnerAgent] Tests %s", "PASSED" if passed else "FAILED")

        validation = state.get("validation_result") or {
            "tests_executed": False,
            "tests_passed": False,
            "failed_reason": None,
            "coverage": None,
            "stages": {}
        }
        validation["tests_executed"] = True
        validation["tests_passed"] = passed
        validation["failed_reason"] = None if passed else "Validation test assertions failed."
        validation["stages"]["tests"] = {
            "status": "passed" if passed else "failed",
            "command": cmd,
            "exit_code": result.exit_code,
            "stdout": result.stdout[:3000],
            "stderr": result.stderr[:3000],
            "reason": None if passed else "Validation test failures occurred inside the sandbox environment."
        }

        catalog = dict(state.get("evidence_catalog") or {})
        eid_test = reg_evidence(
            catalog,
            kind="test_output",
            description=f"Validation tests {'passed' if passed else 'failed'} — exit code {result.exit_code}",
            content=f"cmd: {cmd}\nexit: {result.exit_code}\n{result.stdout[:300]}\n{result.stderr[:100]}",
            source_agent="test_runner_agent",
        )

        return {
            **state,
            "evidence_catalog": catalog,
            "test_result": {
                "success": passed,
                "passed": passed,
                "patch_applied": patch_applied,
                "exit_code": result.exit_code,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:2000],
                "timed_out": result.timed_out,
                "command": cmd,
                "evidence_id": eid_test,
            },
            "validation_result": validation,
            "steps_completed": [*(state.get("steps_completed") or []), "test_runner_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[TestRunnerAgent] Failed: %s", exc, exc_info=True)
        validation = state.get("validation_result") or {
            "tests_executed": False,
            "tests_passed": False,
            "failed_reason": None,
            "coverage": None,
            "stages": {}
        }
        validation["tests_executed"] = True
        validation["tests_passed"] = False
        validation["failed_reason"] = f"Test execution crashed: {exc}"
        validation["stages"]["tests"] = {
            "status": "error",
            "command": "N/A",
            "exit_code": 1,
            "stdout": "",
            "stderr": str(exc),
            "reason": f"Test runner crashed: {exc}"
        }
        return {
            **state,
            "test_result": {
                "success": False,
                "passed": False,
                "error": str(exc)
            },
            "validation_result": validation,
            "steps_completed": [*(state.get("steps_completed") or []), "test_runner_agent"],
        }
