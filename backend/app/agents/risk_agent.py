"""
AutoBug AI — Risk Analysis Agent
==================================
Analyzes AST modifications and unified diffs to assess deployment and regression risks.
"""

from __future__ import annotations

import json
import logging

from app.agents.issue_agent import _extract_json, _get_llm
from app.agents.state import AutoBugState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior release manager and security engineer.
Analyze the provided unified diff patch and compute release risks.

Return ONLY a JSON object:
{
  "risk_level": "low|medium|high",
  "breaking_api": true|false,
  "database_changes": true|false,
  "dependency_changes": true|false,
  "regression_risk": 0.05,
  "reasoning": "Reason for the risk assessment (e.g. One endpoint modified. No API change. No DB migration.)"
}

Analyze carefully:
- breaking_api: True if public function signatures are changed, API route endpoints are modified/removed, or public schemas change.
- database_changes: True if SQL migrations, database model definitions, or db schema queries are modified.
- dependency_changes: True if requirements.txt, package.json, or other lockfiles are modified.
"""


async def risk_agent(state: AutoBugState) -> AutoBugState:
    """Assess deployment risk of the generated patch."""
    logger.info("[RiskAgent] Analyzing patch risk")
    try:
        patch = state.get("patch") or {}
        unified_diff = patch.get("unified_diff", "")

        if not unified_diff:
            return {
                **state,
                "risk_analysis": {
                    "risk_level": "low",
                    "breaking_api": False,
                    "database_changes": False,
                    "dependency_changes": False,
                    "regression_risk": 0.0,
                    "reasoning": "No patch generated.",
                },
                "steps_completed": [*(state.get("steps_completed") or []), "risk_agent"],
                "error": None,
            }

        llm = _get_llm("risk_agent")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Unified Diff:\n{unified_diff}"},
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        risk = _extract_json(content)

        logger.info("[RiskAgent] Calculated Risk: %s", risk.get("risk_level", "low"))

        return {
            **state,
            "risk_analysis": risk,
            "steps_completed": [*(state.get("steps_completed") or []), "risk_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[RiskAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "risk_analysis": {
                "risk_level": "medium",
                "breaking_api": False,
                "database_changes": False,
                "dependency_changes": False,
                "regression_risk": 0.1,
                "reasoning": f"Risk assessment failed: {exc}",
            },
            "steps_completed": [*(state.get("steps_completed") or []), "risk_agent"],
        }
