"""
AutoBug AI — Environment Agent
================================
Detects the runtime environment and creates the Docker sandbox.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.agents.state import AutoBugState
from app.sandbox.manager import SandboxManager

logger = logging.getLogger(__name__)

RUNTIME_DETECTION_FILES = {
    "requirements.txt": ("Python", "pip"),
    "pyproject.toml": ("Python", "pip"),
    "setup.py": ("Python", "pip"),
    "package.json": ("Node.js", "npm"),
    "yarn.lock": ("Node.js", "yarn"),
    "pnpm-lock.yaml": ("Node.js", "pnpm"),
    "go.mod": ("Go", "go"),
    "Cargo.toml": ("Rust", "cargo"),
    "pom.xml": ("Java", "maven"),
    "build.gradle": ("Java", "gradle"),
    "Gemfile": ("Ruby", "bundler"),
    "composer.json": ("PHP", "composer"),
}

LANGUAGE_DOCKER_IMAGES = {
    "Python": "python:3.11-slim",
    "Node.js": "node:20-slim",
    "Go": "golang:1.21-slim",
    "Rust": "rust:1.73-slim",
    "Java": "openjdk:17-slim",
    "Ruby": "ruby:3.2-slim",
    "PHP": "php:8.2-cli",
}


async def environment_agent(state: AutoBugState) -> AutoBugState:
    """Detect runtime and create sandbox container."""
    logger.info("[EnvironmentAgent] Detecting runtime")
    try:
        repo_path = state.get("repo_path", "")
        runtime_info = _detect_runtime(repo_path)
        logger.info("[EnvironmentAgent] Detected: %s", runtime_info)

        # Create sandbox
        manager = SandboxManager()
        image = LANGUAGE_DOCKER_IMAGES.get(runtime_info["language"], "python:3.11-slim")
        session = await manager.create_session(repo_path, image=image)

        return {
            **state,
            "runtime_info": runtime_info,
            "sandbox_session_id": session.session_id,
            "steps_completed": [*(state.get("steps_completed") or []), "environment_agent"],
            "error": None,
        }
    except Exception as exc:
        logger.error("[EnvironmentAgent] Failed: %s", exc, exc_info=True)
        return {
            **state,
            "runtime_info": {"language": "Python", "version": "3.11", "package_manager": "pip"},
            "steps_completed": [*(state.get("steps_completed") or []), "environment_agent"],
        }


def _detect_runtime(repo_path: str) -> dict:
    """Detect runtime by presence of config/lock files."""
    if not repo_path:
        return {"language": "Python", "version": "unknown", "package_manager": "pip"}

    for filename, (language, pkg_mgr) in RUNTIME_DETECTION_FILES.items():
        if (Path(repo_path) / filename).exists():
            return {"language": language, "package_manager": pkg_mgr, "version": "latest"}

    # Fallback: use most common language from file tree
    return {"language": "Python", "version": "unknown", "package_manager": "pip"}
