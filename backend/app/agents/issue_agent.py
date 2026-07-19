"""
AutoBug AI — Issue Agent
==========================
Parses the raw bug report, extracts error type, stack trace, severity,
and reproduction steps using an LLM.
"""

from __future__ import annotations

import json
import logging

from app.agents.state import AutoBugState
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a bug analysis expert. Extract structured information from bug reports.
Return ONLY a valid JSON object with these fields:
{
  "error_type": "<ErrorClass or category>",
  "error_message": "<Exact error message>",
  "stack_trace": "<Extracted stack trace if present>",
  "severity": "<low|medium|high|critical>",
  "affected_component": "<module/file/function if identifiable>",
  "environment": {"os": "...", "runtime": "...", "version": "..."},
  "reproduction_steps": ["step1", "step2", ...],
  "keywords": ["keyword1", "keyword2"]
}
"""


async def issue_agent(state: AutoBugState) -> AutoBugState:
    """Parse and structure the issue report using LLM."""
    logger.info("[IssueAgent] Parsing issue text")
    try:
        llm = _get_llm("issue_agent")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Bug report:\n\n{state['issue_text']}"},
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)

        # Extract JSON from response
        issue_structured = _extract_json(content)
        logger.info("[IssueAgent] Extracted: error_type=%s, severity=%s",
                    issue_structured.get("error_type"), issue_structured.get("severity"))

        return {
            **state,
            "issue_structured": issue_structured,
            "steps_completed": [*(state.get("steps_completed") or []), "issue_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[IssueAgent] Failed: %s", exc, exc_info=True)
        # Fallback: minimal structure
        return {
            **state,
            "issue_structured": {
                "error_type": "Unknown",
                "error_message": state.get("issue_text", ""),
                "severity": "medium",
                "keywords": [],
            },
            "steps_completed": [*(state.get("steps_completed") or []), "issue_agent"],
        }


def _get_llm(agent_name: str):
    cfg = settings.get_agent_model_config(agent_name)
    provider = cfg["provider"]
    model = cfg["model"]
    temperature = cfg["temperature"]
    max_tokens = cfg["max_tokens"]

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model, temperature=temperature, max_tokens=max_tokens,
            anthropic_api_key=settings.anthropic_api_key,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model, temperature=temperature, max_tokens=max_tokens,
            openai_api_key=settings.openai_api_key,
        )
    elif provider == "mistral":
        from langchain_mistralai import ChatMistralAI
        return ChatMistralAI(
            model=model, temperature=temperature, max_tokens=max_tokens,
            mistral_api_key=settings.mistral_api_key,
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model, temperature=temperature,
            google_api_key=settings.google_api_key,
        )


def _extract_json(text: str) -> dict:
    """Extract JSON object from LLM response text."""
    import re
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Find JSON block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"error_type": "Unknown", "error_message": text[:500], "severity": "medium", "keywords": []}
