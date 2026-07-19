"""
AutoBug AI — Build Agent
==========================
Installs project dependencies inside the sandbox container.
"""

from __future__ import annotations

import logging

from app.agents.state import AutoBugState
from app.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)


async def build_agent(state: AutoBugState) -> AutoBugState:
    """Install dependencies and verify the project builds."""
    logger.info("[BuildAgent] Installing dependencies")
    try:
        runtime = state.get("runtime_info") or {}
        language = runtime.get("language", "Python")
        runtime.get("package_manager", "pip")
        repo_path = state.get("repo_path", "")

        manager = SandboxManager()
        session = await manager.create_session(repo_path)

        result = await manager.install_dependencies(session, language)

        build_result = {
            "success": result.success,
            "stdout": result.stdout[:5000],
            "stderr": result.stderr[:2000],
            "command": "dependency installation",
            "exit_code": 0 if result.success else 1,
        }

        validation = state.get("validation_result") or {
            "tests_executed": False,
            "tests_passed": False,
            "failed_reason": None,
            "coverage": None,
            "stages": {}
        }
        validation["stages"]["build"] = {
            "status": "passed" if result.success else "failed",
            "command": "dependency installation",
            "exit_code": 0 if result.success else 1,
            "stdout": result.stdout[:3000],
            "stderr": result.stderr[:3000],
            "reason": None if result.success else "Dependency installation command returned warnings or failed."
        }

        logger.info("[BuildAgent] Build %s", "succeeded" if result.success else "had warnings")
        return {
            **state,
            "build_result": build_result,
            "validation_result": validation,
            "steps_completed": [*(state.get("steps_completed") or []), "build_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[BuildAgent] Failed: %s", exc, exc_info=True)
        validation = state.get("validation_result") or {
            "tests_executed": False,
            "tests_passed": False,
            "failed_reason": None,
            "coverage": None,
            "stages": {}
        }
        validation["stages"]["build"] = {
            "status": "error",
            "command": "dependency installation",
            "exit_code": 1,
            "stdout": "",
            "stderr": str(exc),
            "reason": f"Build crashed: {exc}"
        }
        return {
            **state,
            "build_result": {"success": False, "stdout": "", "stderr": str(exc)},
            "validation_result": validation,
            "steps_completed": [*(state.get("steps_completed") or []), "build_agent"],
        }
