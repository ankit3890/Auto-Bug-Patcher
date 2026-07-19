"""
AutoBug AI — Root Cause Agent
================================
Deep LLM analysis of all evidence to determine the root cause with confidence score.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.agents.issue_agent import _extract_json, _get_llm
from app.agents.state import AutoBugState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert software engineer performing deep root cause analysis.
Analyze all available evidence (reproduction logs, codebase context, issue details) and determine the root cause of the bug.

CRITICAL LANGUAGE RULES:
1. Do NOT say "Bug report confirms", "the report shows", or "the issue confirms". User reports are CLAIMS, not evidence.
2. ALWAYS separate three layers:
   - User reported: What the user said happened (use exact wording or paraphrase)
   - Static analysis indicates: What the code analysis shows
   - Runtime verification: State explicitly whether it was "Available" or "Unavailable"
3. Avoid inventing illustrative or hypothetical code examples (e.g., mock search queries or concrete inputs) unless you directly observed them in the runtime execution logs.
4. Structure the analysis strictly into:
   - Observed: The exact behavior and error traces witnessed in logs/reproduction output (or state 'No runtime evidence available' if not executed).
   - Confirmed: Verifiable facts about the code structure and logic (e.g. 'function X calls Y', 'the filter expression is Z').
   - Potential Effect: The expected impact on application behavior (e.g. 'may return less relevant matches', 'throws NameError').
5. Your "confidence" must reflect evidence tier:
   - Runtime reproduced + tests passed: up to 0.95
   - Runtime reproduced, no tests: up to 0.75
   - No runtime reproduction, static analysis only: up to 0.65
   - No evidence at all: up to 0.40

Return ONLY a JSON object:
{
  "summary": "One sentence root cause description",
  "observed_behavior": "Observed: [exact behavior seen in logs/sandbox]. Confirmed: [facts about code structure]. Potential Effect: [algorithmic/logical impact].",
  "inferred_cause": "Inferred from source code: [logical deduction step-by-step].",
  "fault_file": "path/to/file.py",
  "fault_line": 42,
  "fault_function": "function_name",
  "root_cause_category": "null_pointer|off_by_one|race_condition|type_error|logic_error|missing_endpoint|...",
  "confidence": 0.65,
  "fix_suggestion": "Brief description of the fix needed"
}
"""


async def root_cause_agent(state: AutoBugState) -> AutoBugState:
    """Determine root cause with LLM analysis."""
    logger.info("[RootCauseAgent] Analyzing root cause")
    try:
        issue = state.get("issue_structured", {})
        repro = state.get("reproduction_result", {})
        chunks = state.get("retrieved_chunks", [])
        fault_files = state.get("fault_files", [])
        fault_functions = state.get("fault_functions", [])
        repo_path = state.get("repo_path", "")

        # Read actual file contents for fault files
        file_contents = ""
        for fpath in fault_files[:3]:
            full = Path(repo_path) / fpath if repo_path else Path(fpath)
            try:
                content = full.read_text(encoding="utf-8", errors="ignore")[:2000]
                file_contents += f"\n=== {fpath} ===\n{content}\n"
            except OSError:
                pass

        code_context = "\n\n".join([c.get("content", "")[:400] for c in chunks[:5]])

        # Check if reproduction was blocked by environment or imports
        repro = state.get("reproduction_result") or {}
        repro_failed_reason = repro.get("reproduction_failed_reason")

        is_blocked = False
        if repro_failed_reason and (
            "ModuleNotFoundError" in repro_failed_reason
            or "ImportError" in repro_failed_reason
            or "command not found" in repro_failed_reason.lower()
        ):
            is_blocked = True

        if is_blocked:
            root_cause = {
                "summary": "Validation Blocker",
                "observed_behavior": f"Observed: Reproduction blocked. Confirmed: {repro_failed_reason}. Potential Effect: Application logic was never executed.",
                "inferred_cause": "Root cause analysis incomplete: sandbox environment / imports blocked reproduction.",
                "fault_file": fault_files[0] if fault_files else "",
                "fault_line": 0,
                "fault_function": "",
                "root_cause_category": "validation_blocker",
                "confidence": 0.35,
                "fix_suggestion": "Install missing packages or correct setup scripts.",
            }
            logger.info("[RootCauseAgent] Reproduction blocked — short-circuiting root cause")
            return {
                **state,
                "root_cause": root_cause,
                "steps_completed": [*(state.get("steps_completed") or []), "root_cause_agent"],
                "error": None,
            }

        llm = _get_llm("root_cause_agent")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""
Bug Report:
{json.dumps(issue, indent=2)}

Reproduction Result:
{json.dumps(repro, indent=2)}

Suspected Fault Location:
Files: {fault_files}
Functions: {fault_functions}

Actual File Contents:
{file_contents}

RAG Code Context:
{code_context}
"""},
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        root_cause = _extract_json(content)

        logger.info("[RootCauseAgent] Root cause: %s (confidence=%.2f)",
                    root_cause.get("summary", ""), root_cause.get("confidence", 0))

        return {
            **state,
            "root_cause": root_cause,
            "steps_completed": [*(state.get("steps_completed") or []), "root_cause_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[RootCauseAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "root_cause": {"summary": "Could not determine root cause", "confidence": 0.0},
            "steps_completed": [*(state.get("steps_completed") or []), "root_cause_agent"],
        }
