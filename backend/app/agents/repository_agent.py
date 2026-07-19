"""
AutoBug AI — Repository Agent
================================
Clones the GitHub repository, detects languages, and builds a file tree.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import git

from app.agents.state import AutoBugState
from app.core.config import settings

logger = logging.getLogger(__name__)

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", "target", "vendor"}
EXTENSION_LANGUAGE_MAP = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JavaScript", ".tsx": "TypeScript", ".go": "Go",
    ".java": "Java", ".rs": "Rust", ".cpp": "C++", ".c": "C",
    ".cs": "C#", ".rb": "Ruby", ".php": "PHP",
}


async def repository_agent(state: AutoBugState) -> AutoBugState:
    """Clone repo, detect languages, build file tree."""
    logger.info("[RepositoryAgent] Starting for %s", state.get("repo_url"))
    try:
        repo_url = state["repo_url"]
        repo_id = state.get("repo_id", "default")
        local_path = Path(settings.repos_base_path) / repo_id

        # Format URL with token for authenticated git access
        clone_url = repo_url
        if settings.github_token:
            clone_url = repo_url.replace("https://", f"https://x-access-token:{settings.github_token}@")

        # Clone or pull
        if local_path.exists() and (local_path / ".git").exists():
            repo = git.Repo(str(local_path))
            # Sync remote URL in case token was changed/updated in settings
            repo.remotes.origin.set_url(clone_url)
            repo.remotes.origin.pull()
        else:
            local_path.mkdir(parents=True, exist_ok=True)
            git.Repo.clone_from(clone_url, str(local_path), depth=1)

        # Build file tree
        file_tree: list[str] = []
        lang_counts: dict[str, int] = {}
        for root, dirs, files in os.walk(str(local_path)):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in files:
                rel = os.path.relpath(os.path.join(root, fname), str(local_path))
                file_tree.append(rel.replace("\\", "/"))
                ext = Path(fname).suffix.lower()
                lang = EXTENSION_LANGUAGE_MAP.get(ext)
                if lang:
                    lang_counts[lang] = lang_counts.get(lang, 0) + 1

        logger.info("[RepositoryAgent] Cloned: %d files, languages: %s", len(file_tree), lang_counts)
        return {
            **state,
            "repo_path": str(local_path),
            "repo_file_tree": file_tree,
            "repo_languages": lang_counts,
            "steps_completed": [*(state.get("steps_completed") or []), "repository_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[RepositoryAgent] Failed: %s", exc, exc_info=True)
        return {**state, "error": str(exc), "failed_agent": "repository_agent"}
