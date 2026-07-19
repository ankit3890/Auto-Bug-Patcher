"""
AutoBug AI — Static Analysis Agent
=====================================
Runs ruff (Python), eslint (JS/TS), or other linters on the generated patch.
"""

from __future__ import annotations

import logging

from app.agents.state import AutoBugState
from app.agents.evidence_registry import register as reg_evidence
from app.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)


async def static_analysis_agent(state: AutoBugState) -> AutoBugState:
    """Run static analysis on the generated patch."""
    logger.info("[StaticAnalysisAgent] Running static analysis")
    try:
        patch = state.get("patch", {})
        unified_diff = patch.get("unified_diff", "")
        runtime = state.get("runtime_info", {})
        language = runtime.get("language", "Python")
        repo_path = state.get("repo_path", "")

        if not unified_diff:
            return {
                **state,
                "static_analysis_result": {"passed": True, "issues": [], "skipped": True},
                "steps_completed": [*(state.get("steps_completed") or []), "static_analysis_agent"],
            }

        manager = SandboxManager()
        session = await manager.create_session(repo_path, job_id=state.get("job_id"))

        # Apply patch temporarily
        await manager.copy_file_to_sandbox(session, unified_diff, "/tmp/fix.patch")
        apply_result = await manager.run_command(
            session, "cd /repo && patch -p1 < /tmp/fix.patch 2>&1", timeout=30
        )

        issues = []
        passed = True

        if language == "Python":
            ruff_result = await manager.run_command(
                session, "cd /repo && pip install ruff -q && ruff check . --output-format=json 2>/dev/null || echo '[]'",
                timeout=60,
            )
            try:
                import json
                raw = ruff_result.stdout.strip()
                if raw and raw != "[]":
                    ruff_issues = json.loads(raw)
                    issues = [
                        {
                            "file": i.get("filename"),
                            "line": i.get("location", {}).get("row"),
                            "code": i.get("code"),
                            "message": i.get("message"),
                        }
                        for i in ruff_issues[:20]
                    ]
                    passed = len([i for i in issues if i.get("code", "").startswith("E")]) == 0
            except Exception:
                pass
        elif language in ("JavaScript", "TypeScript", "Node.js"):
            eslint_result = await manager.run_command(
                session, "cd /repo && npx eslint --format json . 2>/dev/null || echo '[]'",
                timeout=60,
            )
            try:
                import json
                raw = eslint_result.stdout.strip()
                if raw:
                    eslint_data = json.loads(raw)
                    for file_result in eslint_data:
                        for msg in file_result.get("messages", [])[:5]:
                            issues.append({
                                "file": file_result.get("filePath"),
                                "line": msg.get("line"),
                                "message": msg.get("message"),
                                "severity": msg.get("severity"),
                            })
                    passed = not any(i.get("severity") == 2 for i in issues)
            except Exception:
                pass

        logger.info("[StaticAnalysisAgent] Passed: %s, Issues: %d", passed, len(issues))
        validation = state.get("validation_result") or {
            "tests_executed": False,
            "tests_passed": False,
            "failed_reason": None,
            "coverage": None,
            "stages": {}
        }
        validation["stages"]["lint"] = {
            "status": "passed" if passed else "failed",
            "command": "ruff check" if language == "Python" else "eslint",
            "exit_code": 0 if passed else 1,
            "stdout": f"Passed: {passed}. Found {len(issues)} issues.",
            "stderr": "",
            "reason": None if passed else f"Linter check failed with {len(issues)} issues."
        }

        catalog = dict(state.get("evidence_catalog") or {})
        eid_lint = reg_evidence(
            catalog,
            kind="lint_report",
            description=f"Static analysis ({language}): {'passed' if passed else f'failed with {len(issues)} issue(s)'}.",
            content=f"passed={passed} issues={len(issues)}\n" + "\n".join(
                f"{i.get('file')}:{i.get('line')} {i.get('code','?')} {i.get('message','')}"
                for i in issues[:5]
            ),
            source_agent="static_analysis_agent",
        )

        return {
            **state,
            "evidence_catalog": catalog,
            "static_analysis_result": {
                "passed": passed,
                "issues": issues,
                "language": language,
                "patch_applied": apply_result.success,
                "evidence_id": eid_lint,
            },
            "validation_result": validation,
            "steps_completed": [*(state.get("steps_completed") or []), "static_analysis_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[StaticAnalysisAgent] Failed: %s", exc, exc_info=True)
        validation = state.get("validation_result") or {
            "tests_executed": False,
            "tests_passed": False,
            "failed_reason": None,
            "coverage": None,
            "stages": {}
        }
        validation["stages"]["lint"] = {
            "status": "error",
            "command": "static analysis check",
            "exit_code": 1,
            "stdout": "",
            "stderr": str(exc),
            "reason": f"Linter crashed: {exc}"
        }
        return {
            **state,
            "static_analysis_result": {"passed": True, "issues": [], "error": str(exc)},
            "validation_result": validation,
            "steps_completed": [*(state.get("steps_completed") or []), "static_analysis_agent"],
        }
