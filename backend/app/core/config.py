"""
AutoBug AI — Application Configuration
=======================================
Loads settings from TWO sources (in priority order):
  1. config.yaml  — AI/model behaviour (change anytime, no rebuild needed)
  2. .env / environment variables — secrets & infrastructure URLs

Pattern: Edit config.yaml to change models/providers. Edit .env for secrets.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import json
import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# YAML config loader — reads config.yaml at startup
# ---------------------------------------------------------------------------

def _load_yaml(path: str) -> dict[str, Any]:
    """Load YAML config file. Returns empty dict if file not found."""
    config_path = Path(path)
    if not config_path.exists():
        # Try relative path from project root
        config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


# ---------------------------------------------------------------------------
# Nested config models (from config.yaml)
# ---------------------------------------------------------------------------

class LLMConfig:
    """Parsed LLM configuration from config.yaml."""

    def __init__(self, data: dict[str, Any]):
        self.provider: str = data.get("provider", "mistral")
        self.model: str = data.get("model", "open-mistral-7b")
        self.fallback_model: str = data.get("fallback_model", "open-mixtral-8x7b")
        self.temperature: float = data.get("temperature", 0.1)
        self.max_tokens: int = data.get("max_tokens", 4096)
        self.top_p: float = data.get("top_p", 0.95)
        self.timeout_seconds: int = data.get("timeout_seconds", 120)
        self.max_retries: int = data.get("max_retries", 3)
        self.retry_delay_seconds: int = data.get("retry_delay_seconds", 2)


class EmbeddingConfig:
    """Parsed embedding configuration from config.yaml."""

    def __init__(self, data: dict[str, Any]):
        self.provider: str = data.get("provider", "mistral")
        self.model: str = data.get("model", "mistral-embed")
        self.dimension: int = data.get("dimension", 1024)
        self.batch_size: int = data.get("batch_size", 64)


class RAGConfig:
    """Parsed RAG configuration from config.yaml."""

    def __init__(self, data: dict[str, Any]):
        self.chunk_size: int = data.get("chunk_size", 512)
        self.chunk_overlap: int = data.get("chunk_overlap", 50)
        self.top_k: int = data.get("top_k", 10)
        self.similarity_threshold: float = data.get("similarity_threshold", 0.65)
        self.collection_prefix: str = data.get("collection_prefix", "autobug_repo_")


class SandboxConfig:
    """Parsed sandbox configuration from config.yaml."""

    def __init__(self, data: dict[str, Any]):
        self.base_image: str = data.get("base_image", "python:3.11-slim")
        self.cpu_quota: int = data.get("cpu_quota", 200000)
        self.memory_limit: str = data.get("memory_limit", "4g")
        self.memory_swap: str = data.get("memory_swap", "4g")
        self.execution_timeout_seconds: int = data.get("execution_timeout_seconds", 600)
        self.build_timeout_seconds: int = data.get("build_timeout_seconds", 300)
        self.network_mode: str = data.get("network_mode", "none")


class PipelineConfig:
    """Parsed pipeline configuration from config.yaml."""

    def __init__(self, data: dict[str, Any]):
        agents_data = data.get("agents", {})
        self.agents: dict[str, bool] = {
            name: agents_data.get(name, True)
            for name in [
                "repository_agent", "issue_agent", "planner_agent",
                "retrieval_agent", "environment_agent", "build_agent",
                "reproduction_agent", "localization_agent", "root_cause_agent",
                "patch_agent", "static_analysis_agent", "test_generator_agent",
                "test_runner_agent", "reviewer_agent", "git_agent",
                "pr_agent", "report_agent",
            ]
        }
        self.require_human_approval: bool = data.get("require_human_approval", True)


class ReportingConfig:
    """Parsed reporting configuration from config.yaml."""

    def __init__(self, data: dict[str, Any]):
        self.formats: list[str] = data.get("formats", ["markdown", "json"])
        self.include_diff: bool = data.get("include_diff", True)
        self.include_execution_logs: bool = data.get("include_execution_logs", True)
        self.include_test_results: bool = data.get("include_test_results", True)
        self.include_confidence_scores: bool = data.get("include_confidence_scores", True)


# ---------------------------------------------------------------------------
# Main Settings class (env vars + secrets)
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    """
    Application settings.

    Secrets come from environment variables / .env file.
    AI/model config comes from config.yaml (via yaml_config property).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- AI Provider Keys ----
    mistral_api_key: str = Field(default="", alias="MISTRAL_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")

    # ---- GitHub ----
    github_token: str = Field(default="", alias="GITHUB_TOKEN")
    github_client_id: str = Field(default="", alias="GITHUB_CLIENT_ID")
    github_client_secret: str = Field(default="", alias="GITHUB_CLIENT_SECRET")
    github_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/github/callback",
        alias="GITHUB_REDIRECT_URI",
    )

    # ---- Database ----
    database_url: str = Field(
        default="postgresql+asyncpg://autobug:autobug_password@localhost:5432/autobug",
        alias="DATABASE_URL",
    )

    # ---- Redis ----
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # ---- Qdrant ----
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")

    # ---- Security ----
    secret_key: str = Field(default="change_me_in_production", alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=10080, alias="JWT_EXPIRE_MINUTES")

    # ---- App ----
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    frontend_url: str = Field(default="http://localhost:3000", alias="FRONTEND_URL")

    # ---- Config YAML path ----
    config_path: str = Field(default="config.yaml", alias="CONFIG_PATH")

    # ---- Storage ----
    repos_base_path: str = Field(default="/tmp/autobug_repos", alias="REPOS_BASE_PATH")

    # ---- Monitoring ----
    langsmith_api_key: str = Field(default="", alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="autobug-ai", alias="LANGSMITH_PROJECT")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")

    # ---- Derived: YAML config (loaded lazily) ----
    _yaml_data: dict[str, Any] = {}

    def model_post_init(self, __context: Any) -> None:
        """Load YAML config after settings are initialized."""
        self._yaml_data = _load_yaml(self.config_path)

    @property
    def yaml(self) -> dict[str, Any]:
        """Raw YAML config data."""
        return self._yaml_data

    @property
    def llm(self) -> LLMConfig:
        """LLM configuration from config.yaml."""
        return LLMConfig(self._yaml_data.get("llm", {}))

    @property
    def embeddings(self) -> EmbeddingConfig:
        """Embedding configuration from config.yaml."""
        return EmbeddingConfig(self._yaml_data.get("embeddings", {}))

    @property
    def rag(self) -> RAGConfig:
        """RAG configuration from config.yaml."""
        return RAGConfig(self._yaml_data.get("rag", {}))

    @property
    def sandbox(self) -> SandboxConfig:
        """Sandbox configuration from config.yaml."""
        return SandboxConfig(self._yaml_data.get("sandbox", {}))

    @property
    def pipeline(self) -> PipelineConfig:
        """Pipeline configuration from config.yaml."""
        return PipelineConfig(self._yaml_data.get("pipeline", {}))

    @property
    def reporting(self) -> ReportingConfig:
        """Reporting configuration from config.yaml."""
        return ReportingConfig(self._yaml_data.get("reporting", {}))

    def get_agent_model_config(self, agent_name: str) -> dict[str, Any]:
        """
        Get per-agent model overrides from config.yaml.
        Falls back to global LLM config if no override defined.
        """
        agent_models = self._yaml_data.get("agent_models", {})
        override = agent_models.get(agent_name, {})
        # Merge with global defaults
        return {
            "model": override.get("model", self.llm.model),
            "temperature": override.get("temperature", self.llm.temperature),
            "max_tokens": override.get("max_tokens", self.llm.max_tokens),
            "provider": override.get("provider", self.llm.provider),
        }

    def get_api_key_for_provider(self, provider: str) -> str:
        """Return the API key for a given provider name."""
        key_map = {
            "mistral": self.mistral_api_key,
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "google": self.google_api_key,
        }
        return key_map.get(provider, "")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    def _get_local_setting(self, env_key: str, default_val: str) -> str:
        """Fetch settings from the local settings file, falling back to default."""
        val = default_val
        try:
            shared_dir = Path(self.repos_base_path)
            local_settings_file = shared_dir / "local_settings.json"
            if local_settings_file.exists():
                with open(local_settings_file) as f:
                    data = json.load(f)
                    val = data.get(env_key) or default_val
        except Exception:
            pass

        if val and isinstance(val, str):
            val_stripped = val.strip("\"'")
            val_lower = val_stripped.lower()
            if "your_" in val_lower or "change_me" in val_lower or "change_this" in val_lower or val_lower == "placeholder":
                return ""
            return val_stripped
        return val or ""

    def __getattribute__(self, name: str) -> Any:
        """Override attribute access to load config dynamically."""
        if name in {
            "mistral_api_key",
            "openai_api_key",
            "anthropic_api_key",
            "google_api_key",
            "github_token",
        }:
            env_key = {
                "mistral_api_key": "MISTRAL_API_KEY",
                "openai_api_key": "OPENAI_API_KEY",
                "anthropic_api_key": "ANTHROPIC_API_KEY",
                "google_api_key": "GOOGLE_API_KEY",
                "github_token": "GITHUB_TOKEN",
            }[name]
            raw_val = super().__getattribute__(name)
            return self._get_local_setting(env_key, raw_val)
        return super().__getattribute__(name)


@lru_cache
def get_settings() -> Settings:
    """
    Returns cached Settings instance.
    Call get_settings.cache_clear() to reload config (e.g., after editing config.yaml).
    """
    return Settings()


# Convenience alias
settings = get_settings()
