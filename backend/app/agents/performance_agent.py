"""
AutoBug AI — Performance Analysis Agent  (Sprint 7)
=====================================================
LLM-powered agent that analyses the patch AST and produces
a structured component-wise performance impact report.
"""

from __future__ import annotations

import json
import logging

from app.agents.issue_agent import _extract_json, _get_llm
from app.agents.state import AutoBugState

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior software performance engineer.
Given a unified diff patch, analyse the performance impact across three components:
- Client Processing (browser JS, frontend rendering)
- Network Overhead (number/size of HTTP requests added or removed)
- Backend Search/Compute (time complexity of new algorithms, DB queries)

CRITICAL RULES:
1. NEVER state measured latency figures unless you actually ran a benchmark — you did not.
2. ALWAYS prefix estimates with "Expected" and give an explicit algorithmic reason.
   GOOD: "Expected: Negligible — algorithm remains O(n) linear scan."
   BAD:  "Minimal improvement" or "5ms faster" (you did not measure this).
3. If the patch does not affect a component, say "No change — component unaffected by this patch."
4. Diff lines starting with '+' are additions, '-' are deletions. Only analyse actual changes.
5. If you cannot determine impact from the diff alone, say "Not benchmarked — manual profiling recommended."

Return ONLY a JSON object:
{
  "components": [
    {
      "component": "Client Processing",
      "complexity_before": "O(1)",
      "complexity_after": "O(k) per keystroke",
      "network_before": "None",
      "network_after": "None",
      "memory_before": "N/A",
      "memory_after": "N/A",
      "latency_delta": "Expected: Minimal — existing DOM manipulation is unchanged"
    },
    {
      "component": "Network Overhead",
      "complexity_before": "0 requests",
      "complexity_after": "1 HTTP GET per keystroke",
      "network_before": "0 requests",
      "network_after": "1 request per input event",
      "memory_before": "N/A",
      "memory_after": "N/A",
      "latency_delta": "Expected: +5-20ms per request — standard HTTP round-trip; not benchmarked"
    },
    {
      "component": "Backend Search",
      "complexity_before": "N/A (endpoint missing)",
      "complexity_after": "O(n) linear scan over title list",
      "network_before": "N/A",
      "network_after": "N/A",
      "memory_before": "O(1)",
      "memory_after": "O(k) for results list",
      "latency_delta": "Expected: Sub-millisecond for small datasets (n < 10,000) — not benchmarked"
    }
  ],
  "summary": "One-sentence summary using 'Expected' language only.",
  "overall_latency_impact": "Expected: Low impact for typical dataset sizes — not benchmarked."
}
"""


async def performance_agent(state: AutoBugState) -> AutoBugState:
    """Analyse patch for performance impact."""
    logger.info("[PerformanceAgent] Analysing patch performance impact")
    try:
        patch = state.get("patch") or {}
        diff = patch.get("unified_diff", "No diff available")
        root_cause = state.get("root_cause") or {}

        llm = _get_llm("performance_agent")
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Patch diff:\n```\n{diff[:4000]}\n```\n\n"
                f"Root cause summary: {root_cause.get('summary', 'N/A')}\n"
                f"Modified files: {patch.get('modified_files', [])}"
            )},
        ]
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        analysis = _extract_json(content)

        # Also backfill patch-level complexity fields for report template compatibility
        components = analysis.get("components", [])
        client = next((c for c in components if "client" in c.get("component", "").lower()), {})
        network = next((c for c in components if "network" in c.get("component", "").lower()), {})
        backend = next((c for c in components if "backend" in c.get("component", "").lower()), {})

        updated_patch = {
            **patch,
            "client_complexity_before": client.get("complexity_before", "O(1)"),
            "client_complexity_after":  client.get("complexity_after",  "O(1)"),
            "network_complexity_before": network.get("network_before", "None"),
            "network_complexity_after":  network.get("network_after",  "None"),
            "backend_complexity_before": backend.get("complexity_before", "Existing"),
            "backend_complexity_after":  backend.get("complexity_after",  "Existing"),
            "latency_impact": analysis.get("overall_latency_impact", "Expected unchanged"),
        }

        return {
            **state,
            "performance_analysis": analysis,
            "patch": updated_patch,
            "steps_completed": [*(state.get("steps_completed") or []), "performance_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[PerformanceAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "performance_analysis": {"components": [], "summary": f"Analysis failed: {exc}", "overall_latency_impact": "Unknown"},
            "steps_completed": [*(state.get("steps_completed") or []), "performance_agent"],
        }
