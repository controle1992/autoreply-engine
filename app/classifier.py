from __future__ import annotations

import logging

from app.industry import get_industry_config
from app.models import Sentiment, Urgency

logger = logging.getLogger(__name__)

VALID_SENTIMENTS = {s.value for s in Sentiment}
VALID_URGENCIES = {u.value for u in Urgency}


def validate_classification(raw: dict) -> dict:
    """Validate and normalize classification fields from LLM output.

    Categories are validated against the loaded industry config.
    """
    industry = get_industry_config()
    result = {}

    # Category — validated against config
    category = raw.get("category", industry.default_category).lower().strip()
    if category not in industry.category_names:
        logger.warning("Invalid category %r, defaulting to %r", category, industry.default_category)
        category = industry.default_category
    result["category"] = category

    # Confidence
    try:
        confidence = float(raw.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.5
    result["confidence"] = round(confidence, 2)

    # Sentiment
    sentiment = raw.get("sentiment", "neutral").lower().strip()
    if sentiment not in VALID_SENTIMENTS:
        logger.warning("Invalid sentiment %r, defaulting to 'neutral'", sentiment)
        sentiment = "neutral"
    result["sentiment"] = sentiment

    # Urgency
    urgency = raw.get("urgency", "medium").lower().strip()
    if urgency not in VALID_URGENCIES:
        logger.warning("Invalid urgency %r, defaulting to 'medium'", urgency)
        urgency = "medium"
    result["urgency"] = urgency

    return result
