from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CategoryConfig(BaseModel):
    name: str
    description: str


class ResponseRule(BaseModel):
    """A business rule that checks and patches the suggested reply for a category."""
    category: str
    instruction: str = ""
    reply_must_contain: list[str] = Field(default_factory=list)
    fallback_prefix: str = ""
    fallback_suffix: str = ""
    ensure_action: str = ""


class IndustryConfig(BaseModel):
    """Full industry configuration loaded from YAML."""
    name: str
    description: str
    language: str = "fr"
    company_name: str = ""

    categories: list[CategoryConfig]
    entities: list[str]
    response_rules: list[ResponseRule] = Field(default_factory=list)

    # Computed helpers
    @property
    def category_names(self) -> set[str]:
        return {c.name for c in self.categories}

    @property
    def default_category(self) -> str:
        """Last category is used as the fallback (typically 'other')."""
        return self.categories[-1].name if self.categories else "other"

    def categories_prompt_string(self) -> str:
        return " | ".join(c.name for c in self.categories)

    def categories_description_block(self) -> str:
        return "\n".join(f"- {c.name}: {c.description}" for c in self.categories)

    def entities_json_block(self) -> str:
        return ",\n    ".join(f'"{e}": ""' for e in self.entities)

    def response_rules_block(self) -> str:
        lines = []
        for rule in self.response_rules:
            if rule.instruction:
                lines.append(f"- Pour la catégorie \"{rule.category}\" : {rule.instruction}")
        return "\n".join(lines)


def load_industry_config(config_path: str) -> IndustryConfig:
    """Load and validate an industry YAML config file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Industry config not found: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    config = IndustryConfig(**raw)
    logger.info(
        "Loaded industry config: %s (%d categories, %d entities, %d rules)",
        config.name,
        len(config.categories),
        len(config.entities),
        len(config.response_rules),
    )
    return config


# Singleton — loaded once at startup, used everywhere
_config: Optional[IndustryConfig] = None


def get_industry_config() -> IndustryConfig:
    global _config
    if _config is None:
        from app.config import settings
        _config = load_industry_config(settings.industry_config)
    return _config


def reload_industry_config() -> IndustryConfig:
    """Force reload (useful for tests)."""
    global _config
    _config = None
    return get_industry_config()
