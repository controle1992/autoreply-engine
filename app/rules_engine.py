from __future__ import annotations

import logging

from app.config import settings
from app.industry import get_industry_config
from app.models import EmailProcessingResult

logger = logging.getLogger(__name__)


def apply_business_rules(result: EmailProcessingResult) -> EmailProcessingResult:
    """Apply deterministic business rules on top of LLM output.

    Rules come from two sources:
    1. Universal rules (low confidence flagging, angry customer escalation)
    2. Industry config response_rules (per-category reply checks)
    """
    industry = get_industry_config()

    # --- Universal: human review for low confidence ---
    if result.confidence < settings.confidence_threshold:
        result.requires_human_review = True
        result.review_reason = (
            f"Confiance faible ({result.confidence:.0%}). "
            "Vérification humaine recommandée."
        )
        if "Transférer à un conseiller pour vérification" not in result.actions:
            result.actions.append("Transférer à un conseiller pour vérification")

    # --- Universal: angry customer escalation ---
    if result.sentiment == "angry" and result.urgency != "high":
        result.urgency = "high"
        logger.info("Escalated urgency to HIGH due to angry sentiment")

    if result.sentiment == "angry":
        if "Escalader au responsable du service client" not in result.actions:
            result.actions.append("Escalader au responsable du service client")

    # --- Industry-specific response rules ---
    for rule in industry.response_rules:
        if result.category != rule.category:
            continue

        # Check if reply must contain certain keywords
        if rule.reply_must_contain:
            reply_lower = result.suggested_reply.lower()
            if not any(m in reply_lower for m in rule.reply_must_contain):
                if rule.fallback_prefix:
                    result.suggested_reply = rule.fallback_prefix + result.suggested_reply
                if rule.fallback_suffix:
                    result.suggested_reply = result.suggested_reply + rule.fallback_suffix

        # Ensure a specific action is present
        if rule.ensure_action:
            if not any(rule.ensure_action.lower() in a.lower() for a in result.actions):
                result.actions.append(rule.ensure_action)

    return result
