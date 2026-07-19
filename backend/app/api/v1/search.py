"""
AutoBug AI — Search API
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.rag.retriever import CodeRetriever

router = APIRouter(prefix="/search", tags=["search"])


class SemanticSearchRequest(BaseModel):
    query: str
    repo_id: str
    top_k: int = 10
    language: str | None = None


class SymbolSearchRequest(BaseModel):
    symbol: str
    repo_id: str


class FileSearchRequest(BaseModel):
    path_fragment: str
    repo_id: str
    limit: int = 20


@router.post("/semantic")
async def semantic_search(payload: SemanticSearchRequest):
    """Semantic code search using embeddings."""
    try:
        retriever = CodeRetriever()
        results = retriever.semantic_search(
            query=payload.query,
            repo_id=payload.repo_id,
            top_k=payload.top_k,
            language_filter=payload.language,
        )
        return {"results": results, "count": len(results)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/symbol")
async def symbol_search(payload: SymbolSearchRequest):
    """Search for a specific code symbol."""
    try:
        retriever = CodeRetriever()
        results = retriever.symbol_search(payload.symbol, payload.repo_id)
        return {"results": results, "count": len(results)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/files")
async def file_search(payload: FileSearchRequest):
    """Fuzzy file path search."""
    try:
        retriever = CodeRetriever()
        results = retriever.file_search(payload.path_fragment, payload.repo_id, payload.limit)
        return {"results": results, "count": len(results)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
