"""
AutoBug AI — Planner Agent
============================
Decomposes the bug into multiple targeted search queries and an execution plan.
"""

from __future__ import annotations

import json
import logging

from app.agents.issue_agent import _extract_json, _get_llm
from app.agents.state import AutoBugState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior software engineer planning a bug investigation.
Given a structured bug report and the repository's language info, generate:
1. A list of 5-8 targeted semantic search queries to find the relevant code
2. A brief investigation plan

Return ONLY a JSON object:
{
  "search_queries": ["query1", "query2", ...],
  "plan_summary": "Brief description of investigation strategy",
  "suspected_areas": ["module/file path hints"]
}
"""


async def planner_agent(state: AutoBugState) -> AutoBugState:
    """Generate search queries and investigation plan."""
    logger.info("[PlannerAgent] Generating search queries")
    try:
        issue = state.get("issue_structured", {})
        languages = state.get("repo_languages", {})
        llm = _get_llm("planner_agent")

        user_content = f"""Bug report analysis:
{json.dumps(issue, indent=2)}

Repository languages: {json.dumps(languages)}
File tree sample (first 50 files):
{chr(10).join((state.get("repo_file_tree") or [])[:50])}
"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        plan = _extract_json(content)

        queries = plan.get("search_queries", [])
        if not queries:
            # Fallback: use keywords from issue
            keywords = issue.get("keywords", [])
            error_type = issue.get("error_type", "error")
            queries = [
                f"{error_type} handler implementation",
                f"{issue.get('affected_component', '')} function definition",
                *[f"{kw} implementation" for kw in keywords[:3]],
            ]

        logger.info("[PlannerAgent] Generated %d search queries", len(queries))
        return {
            **state,
            "search_queries": queries,
            "steps_completed": [*(state.get("steps_completed") or []), "planner_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[PlannerAgent] Failed: %s", exc, exc_info=True)
        # Fallback: basic queries from issue keywords
        issue = state.get("issue_structured", {})
        queries = [
            f"{issue.get('error_type', 'error')} handling",
            str(issue.get("error_message", ""))[:100],
        ]
        return {
            **state,
            "search_queries": queries,
            "steps_completed": [*(state.get("steps_completed") or []), "planner_agent"],
        }
