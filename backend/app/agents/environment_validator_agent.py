"""
AutoBug AI — Environment Validator Agent  (Fix 1 + Fix 2)
===========================================================
Validates the sandbox environment tool-chain BEFORE any reproduction or
validation attempts. Returns a clear environment_result.ready boolean.

If ready == False, the pipeline stops at this node and jumps to report_agent.
"""

from __future__ import annotations

import logging

from app.agents.state import AutoBugState
from app.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)

# (tool_name, check_command, install_command)
REQUIRED_TOOLS: list[tuple[str, str, str]] = [
    ("python",  "python3 --version",             "apt-get update && apt-get install -y python3"),
    ("pip",     "pip --version",                  "apt-get update && apt-get install -y python3-pip"),
    ("pytest",  "python3 -m pytest --version",   "pip install pytest"),
    ("git",     "git --version",                  "apt-get update && apt-get install -y git"),
]

LANGUAGE_EXTRA_TOOLS: dict[str, list[tuple[str, str, str]]] = {
    "Node.js":      [("node", "node --version", "apt-get update && apt-get install -y nodejs"),
                     ("npm",  "npm --version",  "apt-get update && apt-get install -y npm")],
    "JavaScript":   [("node", "node --version", "apt-get update && apt-get install -y nodejs"),
                     ("npm",  "npm --version",  "apt-get update && apt-get install -y npm")],
    "TypeScript":   [("node", "node --version", "apt-get update && apt-get install -y nodejs"),
                     ("npm",  "npm --version",  "apt-get update && apt-get install -y npm")],
    "Java":         [("java",  "java -version",  "apt-get update && apt-get install -y default-jdk"),
                     ("maven", "mvn --version",  "apt-get update && apt-get install -y maven")],
}


async def environment_validator_agent(state: AutoBugState) -> AutoBugState:
    """
    Validate and auto-fix sandbox tool-chain.

    Produces environment_result with:
      ready           : bool   — True only if ALL required tools are available
      tool_results    : list   — per-tool PASS/FAIL/FIXED rows
      installed       : list   — tools already present
      fixed           : list   — tools auto-installed
      still_missing   : list   — tools that could not be installed
      blocking_reason : str    — human-readable reason if ready=False
      setup_logs      : str    — full installation output

    Sets failed_agent = "environment_validator_agent" if not ready, so the
    conditional edge in graph.py can stop the pipeline.
    """
    logger.info("[EnvironmentValidator] Validating sandbox tool-chain")
    repo_path = state.get("repo_path", "")
    runtime = state.get("runtime_info") or {}
    repo_languages = state.get("repo_languages") or {}
    # This gate intentionally runs before EnvironmentAgent; use repository
    # detection to select the project toolchain without deferring validation.
    language = runtime.get("language") or (max(repo_languages, key=repo_languages.get) if repo_languages else "Python")

    tool_rows: list[dict] = []
    installed: list[str] = []
    fixed: list[str] = []
    still_missing: list[str] = []
    setup_log_lines: list[str] = []

    try:
        manager = SandboxManager()
        session = await manager.create_session(repo_path, job_id=state.get("job_id"))

        tools = list(REQUIRED_TOOLS)
        tools.extend(LANGUAGE_EXTRA_TOOLS.get(language, []))

        for tool, check_cmd, install_cmd in tools:
            # Check
            check = await manager.run_command(session, check_cmd, timeout=15)
            if check.exit_code == 0:
                version = check.stdout.strip().splitlines()[0][:60] if check.stdout.strip() else "OK"
                tool_rows.append({"tool": tool, "status": "PASS", "version": version})
                installed.append(tool)
                setup_log_lines.append(f"[PASS]  {tool:<12} {version}")
            else:
                # Try auto-install
                setup_log_lines.append(f"[MISS]  {tool:<12} — installing via: {install_cmd}")
                install = await manager.run_command(
                    session,
                    f"DEBIAN_FRONTEND=noninteractive {install_cmd} 2>&1",
                    timeout=120,
                )
                # Verify after install
                verify = await manager.run_command(session, check_cmd, timeout=15)
                if verify.exit_code == 0:
                    version = verify.stdout.strip().splitlines()[0][:60] if verify.stdout.strip() else "OK"
                    tool_rows.append({"tool": tool, "status": "FIXED", "version": version})
                    fixed.append(tool)
                    setup_log_lines.append(f"[FIXED] {tool:<12} {version}")
                else:
                    err = install.stderr[:200].strip() or install.stdout[:200].strip()
                    tool_rows.append({"tool": tool, "status": "FAIL", "version": None, "error": err})
                    still_missing.append(tool)
                    setup_log_lines.append(f"[FAIL]  {tool:<12} install failed: {err}")

        ready = len(still_missing) == 0

        if not ready:
            blocking_reason = (
                f"Required tools unavailable: {', '.join(still_missing)}. "
                "Pipeline stopped to avoid wasting API calls on unverifiable analysis."
            )
            logger.warning("[EnvironmentValidator] NOT READY — missing: %s", still_missing)
        else:
            blocking_reason = None
            logger.info("[EnvironmentValidator] READY — all %d tools verified", len(installed) + len(fixed))

        environment_result = {
            "ready":            ready,
            "tool_results":     tool_rows,
            "installed":        installed,
            "fixed":            fixed,
            "still_missing":    still_missing,
            "blocking_reason":  blocking_reason,
            "setup_logs":       "\n".join(setup_log_lines),
            "error":            None,
        }

        return {
            **state,
            "environment_result": environment_result,
            # Fix 2: If not ready, mark failed_agent so the conditional edge stops the pipeline
            "failed_agent":      ("environment_validator_agent" if not ready else state.get("failed_agent")),
            "steps_completed":   [*(state.get("steps_completed") or []), "environment_validator_agent"],
            "error":             None,
        }

    except Exception as exc:
        logger.error("[EnvironmentValidator] Crashed: %s", exc, exc_info=True)
        environment_result = {
            "ready":           False,
            "tool_results":    [],
            "installed":       [],
            "fixed":           [],
            "still_missing":   ["unknown"],
            "blocking_reason": f"Environment validator crashed: {exc}",
            "setup_logs":      "",
            "error":           str(exc),
        }
        return {
            **state,
            "environment_result": environment_result,
            "failed_agent":       "environment_validator_agent",
            "steps_completed":    [*(state.get("steps_completed") or []), "environment_validator_agent"],
        }
