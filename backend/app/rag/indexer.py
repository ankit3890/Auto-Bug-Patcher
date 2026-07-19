"""
AutoBug AI — RAG Indexer
========================
Clones a GitHub repo, parses source files, generates embeddings
and upserts them into a Qdrant collection for semantic search.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Any

import git
from langchain.text_splitter import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client import models as qmodels

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Language detection by extension
# ---------------------------------------------------------------------------
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JavaScript", ".tsx": "TypeScript", ".go": "Go",
    ".java": "Java", ".rs": "Rust", ".cpp": "C++", ".c": "C",
    ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    ".kt": "Kotlin", ".scala": "Scala", ".sh": "Shell",
    ".yaml": "YAML", ".yml": "YAML", ".json": "JSON",
    ".md": "Markdown", ".html": "HTML", ".css": "CSS",
}

SKIP_DIRS = {
    ".git", ".github", "node_modules", "__pycache__", ".venv", "venv",
    "env", "dist", "build", ".next", ".nuxt", "target", "vendor",
    ".idea", ".vscode", "coverage", ".mypy_cache", ".pytest_cache",
}

SKIP_EXTENSIONS = {".lock", ".sum", ".mod", ".png", ".jpg", ".jpeg",
                   ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf",
                   ".eot", ".pdf", ".zip", ".tar", ".gz", ".pyc"}

MAX_FILE_SIZE_BYTES = 500_000  # 500 KB — skip very large files


class RepositoryIndexer:
    """
    Indexes a GitHub repository into Qdrant for semantic code search.

    Usage::
        indexer = RepositoryIndexer()
        collection = await indexer.index_repository("https://github.com/owner/repo", repo_id)
    """

    def __init__(self) -> None:
        self.qdrant = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
        self.chunk_size = settings.rag.chunk_size
        self.chunk_overlap = settings.rag.chunk_overlap
        self.collection_prefix = settings.rag.collection_prefix

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def index_repository(
        self,
        github_url: str,
        repo_id: str,
        branch: str = "main",
        progress_callback: Any = None,
    ) -> dict[str, Any]:
        """
        Full indexing pipeline: clone → parse → embed → upsert.
        Returns indexing stats.
        """
        collection_name = f"{self.collection_prefix}{repo_id}"
        local_path = Path(settings.repos_base_path) / repo_id

        stats: dict[str, Any] = {
            "repo_id": repo_id,
            "collection": collection_name,
            "files_indexed": 0,
            "chunks_indexed": 0,
            "languages": {},
            "errors": [],
        }

        try:
            # 1. Clone / update repo
            logger.info("Cloning %s → %s", github_url, local_path)
            local_path = await self._clone_or_pull(github_url, str(local_path), branch)
            if progress_callback:
                await progress_callback("cloned", 10)

            # 2. Collect source files
            files = self._collect_files(local_path)
            logger.info("Found %d indexable source files", len(files))
            if progress_callback:
                await progress_callback("files_collected", 20)

            # 3. Create/recreate Qdrant collection
            dimension = settings.embeddings.dimension
            await self._ensure_collection(collection_name, dimension)

            # 4. Chunk & embed in batches
            embedder = self._get_embedder()
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )

            points: list[qmodels.PointStruct] = []
            for idx, file_path in enumerate(files):
                try:
                    chunks = self._chunk_file(file_path, local_path, splitter)
                    if not chunks:
                        continue

                    texts = [c["content"] for c in chunks]
                    embeddings = embedder.embed_documents(texts)

                    for chunk, embedding in zip(chunks, embeddings):
                        point_id = self._make_point_id(repo_id, chunk["file"], chunk["chunk_index"])
                        points.append(
                            qmodels.PointStruct(
                                id=point_id,
                                vector=embedding,
                                payload=chunk,
                            )
                        )

                    lang = chunk.get("language", "Unknown")
                    stats["languages"][lang] = stats["languages"].get(lang, 0) + 1
                    stats["files_indexed"] += 1

                except Exception as exc:
                    logger.warning("Failed to index %s: %s", file_path, exc)
                    stats["errors"].append(str(exc))

                if progress_callback and idx % 20 == 0:
                    pct = 20 + int((idx / len(files)) * 70)
                    await progress_callback("indexing", pct)

            # 5. Upsert all points
            if points:
                batch_size = settings.embeddings.batch_size
                for i in range(0, len(points), batch_size):
                    self.qdrant.upsert(
                        collection_name=collection_name,
                        points=points[i : i + batch_size],
                    )
                stats["chunks_indexed"] = len(points)

            if progress_callback:
                await progress_callback("indexed", 100)

            logger.info(
                "Indexed %d files / %d chunks into %s",
                stats["files_indexed"],
                stats["chunks_indexed"],
                collection_name,
            )

        except Exception as exc:
            logger.error("Indexing failed for %s: %s", github_url, exc, exc_info=True)
            stats["errors"].append(str(exc))
            raise

        return stats

    def delete_collection(self, repo_id: str) -> None:
        """Remove the Qdrant collection for a repo."""
        collection_name = f"{self.collection_prefix}{repo_id}"
        try:
            self.qdrant.delete_collection(collection_name)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _clone_or_pull(self, url: str, path: str, branch: str) -> str:
        """Clone repo if not present, otherwise pull latest."""
        import asyncio
        loop = asyncio.get_event_loop()

        def _sync_clone_or_pull() -> str:
            clone_url = url
            if settings.github_token and "github.com" in url:
                clone_url = url.replace("https://", f"https://{settings.github_token}@")

            if Path(path).exists() and (Path(path) / ".git").exists():
                repo = git.Repo(path)
                if settings.github_token and "github.com" in repo.remotes.origin.url and settings.github_token not in repo.remotes.origin.url:
                    repo.remotes.origin.set_url(clone_url)
                repo.remotes.origin.pull(branch)
            else:
                Path(path).mkdir(parents=True, exist_ok=True)
                git.Repo.clone_from(clone_url, path, branch=branch, depth=1)
            return path

        return await loop.run_in_executor(None, _sync_clone_or_pull)

    def _collect_files(self, base_path: str) -> list[str]:
        """Walk repo and collect indexable source files."""
        result: list[str] = []
        for root, dirs, files in os.walk(base_path):
            # Prune skip dirs in-place
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for fname in files:
                ext = Path(fname).suffix.lower()
                if ext in SKIP_EXTENSIONS:
                    continue
                full_path = os.path.join(root, fname)
                if os.path.getsize(full_path) > MAX_FILE_SIZE_BYTES:
                    continue
                result.append(full_path)
        return result

    def _chunk_file(
        self,
        file_path: str,
        base_path: str,
        splitter: RecursiveCharacterTextSplitter,
    ) -> list[dict[str, Any]]:
        """Read file, split into chunks, return chunk metadata dicts."""
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except OSError:
            return []

        if not content.strip():
            return []

        rel_path = os.path.relpath(file_path, base_path)
        ext = Path(file_path).suffix.lower()
        language = EXTENSION_LANGUAGE_MAP.get(ext, "Unknown")

        chunks = splitter.split_text(content)
        result = []
        for i, chunk_text in enumerate(chunks):
            result.append({
                "content": chunk_text,
                "file": rel_path.replace("\\", "/"),
                "language": language,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "file_path": file_path,
            })
        return result

    async def _ensure_collection(self, name: str, dimension: int) -> None:
        """Create Qdrant collection if it doesn't exist."""
        import asyncio
        loop = asyncio.get_event_loop()

        def _sync_ensure() -> None:
            existing = [c.name for c in self.qdrant.get_collections().collections]
            if name not in existing:
                self.qdrant.create_collection(
                    collection_name=name,
                    vectors_config=qmodels.VectorParams(
                        size=dimension,
                        distance=qmodels.Distance.COSINE,
                    ),
                )

        await loop.run_in_executor(None, _sync_ensure)

    def _get_embedder(self) -> Any:
        """Return the configured embedding model."""
        provider = settings.embeddings.provider
        model = settings.embeddings.model

        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=model,
                openai_api_key=settings.openai_api_key,
            )
        elif provider == "mistral":
            from langchain_mistralai import MistralAIEmbeddings
            return MistralAIEmbeddings(
                model=model,
                mistral_api_key=settings.mistral_api_key,
            )
        else:
            # Fallback: sentence-transformers local model
            from langchain_community.embeddings import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    @staticmethod
    def _make_point_id(repo_id: str, file_path: str, chunk_index: int) -> int:
        """Generate a deterministic integer point ID."""
        raw = f"{repo_id}:{file_path}:{chunk_index}"
        return int(hashlib.md5(raw.encode()).hexdigest(), 16) % (2**63)
