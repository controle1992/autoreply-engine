from __future__ import annotations

from typing import Literal, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # LLM provider:
    #   "anthropic" — Anthropic Claude
    #   "openai"    — OpenAI ChatGPT + any OpenAI-compatible API
    #                  (DeepSeek, Mistral, xAI/Grok, Groq, Together AI, Fireworks, Perplexity,
    #                   Ollama, vLLM, llama.cpp, LM Studio)
    #   "google"    — Google Gemini
    llm_provider: Literal["anthropic", "openai", "google"] = "anthropic"

    # Base URL for OpenAI-compatible APIs (ignored for anthropic/google)
    # Leave empty/None to use OpenAI's default (https://api.openai.com/v1)
    llm_base_url: Optional[str] = None

    # API keys — only the one matching your provider is required
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    # Industry config YAML file path
    industry_config: str = "configs/utilities.yaml"

    # Model name (e.g. "claude-sonnet-4-20250514", "gpt-4o", "gemini-2.0-flash", "deepseek-chat")
    model_name: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.2

    # Confidence threshold below which we flag for human review
    confidence_threshold: float = 0.6

    # Logging
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
