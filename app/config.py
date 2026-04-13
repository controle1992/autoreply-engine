from __future__ import annotations

from typing import Literal, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # LLM provider: "anthropic" for Claude, "openai" for any OpenAI-compatible API (Ollama, vLLM, llama.cpp, etc.)
    llm_provider: Literal["anthropic", "openai"] = "anthropic"

    # Base URL for OpenAI-compatible APIs (e.g. http://localhost:11434/v1 for Ollama)
    llm_base_url: Optional[str] = None

    # API keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Industry config YAML file path
    industry_config: str = "configs/utilities.yaml"

    # Model name (e.g. "claude-sonnet-4-20250514" or "llama3.1:8b")
    model_name: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.2

    # Confidence threshold below which we flag for human review
    confidence_threshold: float = 0.6

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
