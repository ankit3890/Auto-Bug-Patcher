"""
AutoBug AI — Localization Agent
=================================
Narrows down the bug to specific files and functions using AST + RAG.
"""

from __future__ import annotations

import json
import logging

from app.agents.issue_agent import _extract_json, _get_llm
from app.agents.state import AutoBugState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a code debugger performing fault localization.
Given a bug report, stack trace, reproduction output, and relevant code chunks,
identify the most likely faulty files and functions.

Return ONLY a JSON object:
{
  "fault_files": ["path/to/file.py", ...],
  "fault_functions": ["function_name", ...],
  "localization_confidence": 0.85,
  "reasoning": "Brief explanation"
}
"""


async def localization_agent(state: AutoBugState) -> AutoBugState:
    """Narrow down fault location using evidence."""
    logger.info("[LocalizationAgent] Localizing fault")
    try:
        issue = state.get("issue_structured", {})
        repro = state.get("reproduction_result", {})
        chunks = state.get("retrieved_chunks", [])

        code_context = "\n\n".join([
            f"File: {c.get('file')}\n{c.get('content', '')[:400]}"
            for c in chunks[:8]
        ])

        llm = _get_llm("localization_agent")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""
Bug analysis:
{json.dumps(issue, indent=2)}

Reproduction output:
{json.dumps(repro, indent=2)}

Relevant code chunks:
{code_context}
"""},
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        result = _extract_json(content)

        logger.info("[LocalizationAgent] Fault files: %s", result.get("fault_files", []))
        return {
            **state,
            "fault_files": result.get("fault_files", []),
            "fault_functions": result.get("fault_functions", []),
            "steps_completed": [*(state.get("steps_completed") or []), "localization_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[LocalizationAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "fault_files": [],
            "fault_functions": [],
            "steps_completed": [*(state.get("steps_completed") or []), "localization_agent"],
        }
