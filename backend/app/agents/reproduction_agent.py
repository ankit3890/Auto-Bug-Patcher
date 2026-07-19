"""
AutoBug AI — Reproduction Agent
=================================
Attempts to reproduce the bug inside the Docker sandbox.
"""

from __future__ import annotations

import json
import logging

from app.agents.issue_agent import _extract_json, _get_llm
from app.agents.state import AutoBugState
from app.agents.evidence_registry import register as reg_evidence
from app.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a software QA engineer. Given a bug report, generate a minimal shell command
to reproduce the bug inside a Linux Docker container where the repo is at /repo.
Return ONLY a JSON object:
{
  "command": "cd /repo && python -m pytest tests/test_x.py::test_y -x 2>&1",
  "explanation": "Why this command should trigger the bug"
}
"""


async def reproduction_agent(state: AutoBugState) -> AutoBugState:
    """Try to reproduce the bug in sandbox."""
    logger.info("[ReproductionAgent] Attempting to reproduce bug")
    try:
        issue = state.get("issue_structured", {})
        chunks = state.get("retrieved_chunks", [])
        code_context = "\n\n".join([c.get("content", "")[:500] for c in chunks[:5]])

        llm = _get_llm("reproduction_agent")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Bug:\n{json.dumps(issue)}\n\nCode context:\n{code_context}"},
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        plan = _extract_json(content)
        command = plan.get("command", "echo 'No reproduction command generated'")

        # Run in sandbox
        manager = SandboxManager()
        repo_path = state.get("repo_path", "")
        session = await manager.create_session(repo_path, job_id=state.get("job_id"))
        result = await manager.run_command(session, command, timeout=120)

        reproduced = result.exit_code != 0
        reproduction_failed_reason = None
        logger.info("[ReproductionAgent] Exit code: %d", result.exit_code)

        # Extract QA observed vs expected facts using LLM
        observed_behavior = "Execution succeeded" if result.exit_code == 0 else "Execution failed with non-zero exit code"
        expected_behavior = "Successful execution"
        try:
            extraction_prompt = f"""You are a QA engineer analyzing reproduction logs.
Bug Description:
{json.dumps(issue, indent=2)}

Command Executed:
{command}

Execution Exit Code: {result.exit_code}
Execution Output (Stdout/Stderr):
{result.stdout[:2000]}
{result.stderr[:1000]}

Your task is to classify whether the bug reproduction was successful OR if it failed due to sandbox/environment issues.
Classify reproduction as FAILED if:
- The command failed because pytest, jest, or another testing tool is not installed (e.g. command not found).
- The command failed due to a missing Python package/library (ModuleNotFoundError / ImportError).
- The command failed due to a syntax/compilation error in the test file itself rather than a logical error in the application.

Otherwise, if it successfully ran and triggered the assertion failure or UI error described in the bug, classify as SUCCESS.

Return ONLY a JSON object:
{{
  "reproduction_status": "SUCCESS|FAILED",
  "failure_reason": "Brief description of sandbox environment failure (e.g. pytest missing / package missing), or null if SUCCESS.",
  "observed_behavior": "Describe what actually happened (observed facts, inputs, outputs, stacktraces, or logs).",
  "expected_behavior": "Describe what should have happened according to the bug report."
}}
"""
            extract_messages = [
                {"role": "system", "content": "You classify test execution outputs and extract QA reproduction details. Output ONLY JSON."},
                {"role": "user", "content": extraction_prompt}
            ]
            extract_response = llm.invoke(extract_messages)
            extract_content = extract_response.content if hasattr(extract_response, "content") else str(extract_response)
            facts = _extract_json(extract_content)
            
            repro_status = facts.get("reproduction_status", "SUCCESS")
            if repro_status == "FAILED":
                reproduced = False
                reproduction_failed_reason = facts.get("failure_reason") or "Sandbox environment error"
            else:
                reproduced = (result.exit_code != 0)
                
            observed_behavior = facts.get("observed_behavior", observed_behavior)
            expected_behavior = facts.get("expected_behavior", expected_behavior)
        except Exception as e:
            logger.warning("[ReproductionAgent] Failed to extract facts via LLM: %s", e)

        catalog = dict(state.get("evidence_catalog") or {})

        # Fix 8: Register terminal log evidence
        eid_log = reg_evidence(
            catalog,
            kind="terminal_log",
            description=f"Sandbox reproduction — exit code {result.exit_code}, command: {command[:80]}",
            content=f"{result.stdout[:300]}\n{result.stderr[:200]}",
            source_agent="reproduction_agent",
        )
        # Fix 8: Register observed vs expected summary
        eid_obs = reg_evidence(
            catalog,
            kind="stacktrace",
            description=f"Observed: {observed_behavior[:100]} | Expected: {expected_behavior[:100]}",
            content=f"observed: {observed_behavior}\nexpected: {expected_behavior}",
            source_agent="reproduction_agent",
        )

        return {
            **state,
            "evidence_catalog": catalog,
            "reproduction_result": {
                "reproduced": reproduced,
                "reproduction_failed_reason": reproduction_failed_reason,
                "command": command,
                "exit_code": result.exit_code,
                "stdout": result.stdout[:3000],
                "stderr": result.stderr[:3000],
                "observed_behavior": observed_behavior,
                "expected_behavior": expected_behavior,
                "request_details": "Ran reproduction command inside container sandbox.",
                "evidence_ids": [eid_log, eid_obs],
            },
            "steps_completed": [*(state.get("steps_completed") or []), "reproduction_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[ReproductionAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "reproduction_result": {"reproduced": False, "error": str(exc)},
            "steps_completed": [*(state.get("steps_completed") or []), "reproduction_agent"],
        }
