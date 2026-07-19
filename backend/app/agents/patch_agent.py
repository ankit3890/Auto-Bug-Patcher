"""
AutoBug AI — Patch Agent
==========================
Generates a minimal unified diff patch to fix the identified bug.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.agents.issue_agent import _extract_json, _get_llm
from app.agents.state import AutoBugState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert software engineer generating a bug fix patch.
Given the root cause analysis and relevant code, produce a minimal unified diff patch.

Return ONLY a JSON object:
{
  "unified_diff": "--- a/path/file.py\\n+++ b/path/file.py\\n@@ ... @@\\n...",
  "modified_files": ["path/file.py"],
  "patch_summary": "Human-readable explanation of what was changed and why",
  "is_minimal": true,
  "client_complexity_before": "e.g., O(1)",
  "client_complexity_after": "e.g., O(k) (rendering suggestions)",
  "network_complexity_before": "e.g., None",
  "network_complexity_after": "e.g., 1 HTTP request",
  "backend_complexity_before": "e.g., Existing endpoint",
  "backend_complexity_after": "e.g., O(n) over titles",
  "latency_impact": "e.g., Expected unchanged"
}

Rules:
- The diff must be syntactically correct unified diff format
- Change ONLY what is necessary to fix the bug
- Do NOT refactor unrelated code
- Include proper context lines (3 lines before/after each change)
"""


async def patch_agent(state: AutoBugState) -> AutoBugState:
    """Generate a minimal code fix patch."""
    logger.info("[PatchAgent] Generating patch")
    try:
        root_cause = state.get("root_cause") or {}
        issue = state.get("issue_structured") or {}
        chunks = state.get("retrieved_chunks") or []
        fault_files = state.get("fault_files") or []
        repo_path = state.get("repo_path", "")

        # Read fault file contents
        file_contents = {}
        for fpath in fault_files[:3]:
            full = Path(repo_path) / fpath if repo_path else Path(fpath)
            try:
                file_contents[fpath] = full.read_text(encoding="utf-8", errors="ignore")[:4000]
            except OSError:
                pass

        # Also include highly scored RAG chunks
        rag_context = "\n\n".join([
            f"# {c.get('file')} (score={c.get('score', 0):.2f})\n{c.get('content', '')[:600]}"
            for c in chunks[:6]
        ])

        llm = _get_llm("patch_agent")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"""
Root Cause:
{json.dumps(root_cause, indent=2)}

Bug Description:
{json.dumps(issue, indent=2)}

Faulty File Contents:
{json.dumps(file_contents, indent=2)}

Additional Context:
{rag_context}
"""},
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        patch_data = _extract_json(content)

        logger.info("[PatchAgent] Generated patch for files: %s", patch_data.get("modified_files", []))
        return {
            **state,
            "patch": patch_data,
            "steps_completed": [*(state.get("steps_completed") or []), "patch_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[PatchAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "patch": {"unified_diff": "", "modified_files": [], "patch_summary": f"Patch generation failed: {exc}"},
            "steps_completed": [*(state.get("steps_completed") or []), "patch_agent"],
        }
