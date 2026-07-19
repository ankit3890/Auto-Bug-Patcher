"""
AutoBug AI — Code Retriever
============================
Semantic + symbol + file search against the Qdrant vector store.
"""

from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client import models as qmodels

from app.core.config import settings

logger = logging.getLogger(__name__)


class CodeRetriever:
    """
    Retrieves relevant code chunks from Qdrant for a given repository.
    """

    def __init__(self) -> None:
        self.qdrant = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
        self.top_k = settings.rag.top_k
        self.threshold = settings.rag.similarity_threshold
        self.collection_prefix = settings.rag.collection_prefix

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def semantic_search(
        self,
        query: str,
        repo_id: str,
        top_k: int | None = None,
        language_filter: str | None = None,
        file_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Embed the query and search Qdrant for the most similar code chunks.
        Returns list of chunk dicts with similarity scores.
        """
        collection = f"{self.collection_prefix}{repo_id}"
        k = top_k or self.top_k

        embedding = self._embed(query)

        query_filter = self._build_filter(language_filter, file_filter)

        results = self.qdrant.search(
            collection_name=collection,
            query_vector=embedding,
            limit=k,
            score_threshold=self.threshold,
            query_filter=query_filter,
            with_payload=True,
        )

        return [
            {
                **hit.payload,
                "score": hit.score,
            }
            for hit in results
        ]

    def symbol_search(
        self,
        symbol_name: str,
        repo_id: str,
    ) -> list[dict[str, Any]]:
        """
        Search for a specific function/class/variable name using payload filter
        + semantic re-ranking.
        """
        # Build semantic query around the symbol
        query = f"function class definition of {symbol_name}"

        # Broad semantic search with lower threshold
        collection = f"{self.collection_prefix}{repo_id}"
        embedding = self._embed(query)

        results = self.qdrant.search(
            collection_name=collection,
            query_vector=embedding,
            limit=self.top_k * 2,
            score_threshold=0.4,
            with_payload=True,
        )

        # Re-rank: boost chunks that literally contain the symbol name
        symbol_lower = symbol_name.lower()
        ranked = []
        for hit in results:
            content = (hit.payload.get("content") or "").lower()
            boost = 0.2 if symbol_lower in content else 0.0
            ranked.append({
                **hit.payload,
                "score": min(1.0, hit.score + boost),
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[: self.top_k]

    def file_search(
        self,
        path_fragment: str,
        repo_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Fuzzy file path search using payload scroll (no embedding needed).
        Returns unique file entries matching the fragment.
        """
        collection = f"{self.collection_prefix}{repo_id}"
        fragment_lower = path_fragment.lower()

        # Scroll through all payloads looking for path matches
        # (efficient for small repos; for huge repos use a dedicated payload index)
        scroll_results, _ = self.qdrant.scroll(
            collection_name=collection,
            scroll_filter=None,
            limit=5000,
            with_payload=True,
            with_vectors=False,
        )

        seen_files: set[str] = set()
        matches: list[dict[str, Any]] = []
        for point in scroll_results:
            file_path = (point.payload or {}).get("file", "")
            if fragment_lower in file_path.lower() and file_path not in seen_files:
                seen_files.add(file_path)
                matches.append({
                    "file": file_path,
                    "language": point.payload.get("language", "Unknown"),
                })
                if len(matches) >= limit:
                    break

        return matches

    def multi_query_search(
        self,
        queries: list[str],
        repo_id: str,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Run multiple queries and merge/deduplicate results.
        Useful when the planner generates multiple search angles.
        """
        seen: dict[str, dict[str, Any]] = {}
        for query in queries:
            results = self.semantic_search(query, repo_id, top_k=top_k)
            for r in results:
                key = f"{r['file']}:{r['chunk_index']}"
                if key not in seen or r["score"] > seen[key]["score"]:
                    seen[key] = r

        merged = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        return merged[: (top_k or self.top_k)]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _embed(self, text: str) -> list[float]:
        """Generate embedding for a single text string."""
        provider = settings.embeddings.provider
        model = settings.embeddings.model

        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            embedder = OpenAIEmbeddings(
                model=model,
                openai_api_key=settings.openai_api_key,
            )
        elif provider == "mistral":
            from langchain_mistralai import MistralAIEmbeddings
            embedder = MistralAIEmbeddings(
                model=model,
                mistral_api_key=settings.mistral_api_key,
            )
        else:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            embedder = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        return embedder.embed_query(text)

    @staticmethod
    def _build_filter(
        language: str | None,
        file_fragment: str | None,
    ) -> qmodels.Filter | None:
        conditions = []
        if language:
            conditions.append(
                qmodels.FieldCondition(
                    key="language",
                    match=qmodels.MatchValue(value=language),
                )
            )
        if not conditions:
            return None
        return qmodels.Filter(must=conditions)
