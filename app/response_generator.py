from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def validate_response(raw: dict) -> dict:
    """Validate and normalize the suggested reply and summary from LLM output."""
    result = {}

    # Summary
    summary = raw.get("summary", "")
    if not isinstance(summary, str) or not summary.strip():
        summary = "Demande client à analyser manuellement."
        logger.warning("Missing or empty summary, using fallback")
    result["summary"] = summary.strip()

    # Suggested reply
    reply = raw.get("suggested_reply", "")
    if not isinstance(reply, str) or not reply.strip():
        reply = (
            "Madame, Monsieur,\n\n"
            "Nous avons bien reçu votre message et nous vous en remercions. "
            "Un conseiller prendra contact avec vous dans les plus brefs délais "
            "pour traiter votre demande.\n\n"
            "Cordialement,\n"
            "Le Service Client"
        )
        logger.warning("Missing or empty reply, using generic fallback")
    result["suggested_reply"] = reply.strip()

    # Actions
    actions = raw.get("actions", [])
    if not isinstance(actions, list):
        actions = [str(actions)] if actions else []
    result["actions"] = [str(a).strip() for a in actions if a]

    return result
