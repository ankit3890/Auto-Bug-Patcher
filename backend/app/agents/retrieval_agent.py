"""
AutoBug AI — Retrieval Agent
==============================
Runs multi-query RAG search and returns top-k relevant code chunks.
"""

from __future__ import annotations

import logging

from app.agents.state import AutoBugState
from app.rag.retriever import CodeRetriever

logger = logging.getLogger(__name__)


async def retrieval_agent(state: AutoBugState) -> AutoBugState:
    """Retrieve relevant code chunks via semantic search."""
    logger.info("[RetrievalAgent] Running semantic search")
    try:
        retriever = CodeRetriever()
        repo_id = state.get("repo_id", "default")
        queries = state.get("search_queries", [])

        if not queries:
            return {
                **state,
                "retrieved_chunks": [],
                "steps_completed": [*(state.get("steps_completed") or []), "retrieval_agent"],
            }

        chunks = retriever.multi_query_search(queries, repo_id, top_k=15)
        logger.info("[RetrievalAgent] Retrieved %d chunks", len(chunks))

        return {
            **state,
            "retrieved_chunks": chunks,
            "steps_completed": [*(state.get("steps_completed") or []), "retrieval_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[RetrievalAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "retrieved_chunks": [],
            "steps_completed": [*(state.get("steps_completed") or []), "retrieval_agent"],
        }
