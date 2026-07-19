"""
AutoBug AI — Evidence Registry  (Fix 8)
=========================================
Central catalog of auditable evidence items.
Agents call register() to create EV-xxx IDs.
Every claim in the report can then reference an evidence ID.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register(
    catalog: dict,
    kind: str,
    description: str,
    content: str,
    source_agent: str,
) -> str:
    """
    Add an evidence item to the catalog and return its EV-ID.

    Parameters
    ----------
    catalog : dict
        The evidence_catalog dict from AutoBugState (mutated in place).
    kind : str
        One of: terminal_log | http_response | stacktrace | code_snippet |
                lint_report | test_output | browser_log
    description : str
        One-sentence human-readable description of what this evidence shows.
    content : str
        Truncated evidence content (max 500 chars). Keep it short — reports
        reference the ID, not the full content.
    source_agent : str
        Name of the agent that captured this evidence.

    Returns
    -------
    str
        Evidence ID string, e.g. "EV-001".
    """
    idx = len(catalog) + 1
    eid = f"EV-{idx:03d}"
    catalog[eid] = {
        "kind": kind,
        "description": description,
        "content": content[:500],      # truncated excerpt only
        "source_agent": source_agent,
    }
    logger.debug("[EvidenceRegistry] Registered %s (%s) from %s", eid, kind, source_agent)
    return eid


def get_summary(catalog: dict) -> str:
    """Return a compact human-readable summary of all registered evidence."""
    if not catalog:
        return "No evidence registered."
    lines = []
    for eid, item in catalog.items():
        lines.append(f"  {eid}: [{item.get('kind', 'unknown')}] {item.get('description', '')}")
    return "\n".join(lines)
