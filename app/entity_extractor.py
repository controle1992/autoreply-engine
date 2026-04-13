from __future__ import annotations

import logging

from app.industry import get_industry_config

logger = logging.getLogger(__name__)


def validate_entities(raw: dict) -> dict[str, str]:
    """Validate and normalize extracted entities from LLM output.

    Entity fields come from the industry config.
    Ensures all fields are strings and strips whitespace.
    Missing fields default to empty string.
    """
    industry = get_industry_config()
    entities_raw = raw.get("entities", {})
    if not isinstance(entities_raw, dict):
        logger.warning("entities field is not a dict, using empty entities")
        entities_raw = {}

    cleaned = {}
    for field in industry.entities:
        value = entities_raw.get(field, "")
        if not isinstance(value, str):
            value = str(value) if value is not None else ""
        cleaned[field] = value.strip()

    return cleaned
