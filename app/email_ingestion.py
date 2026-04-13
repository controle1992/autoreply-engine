from __future__ import annotations

import logging
import re

from app.models import EmailInput

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Normalize whitespace and strip signatures/disclaimers."""
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip common email signatures
    for marker in ["--", "___", "Envoyé depuis", "Sent from"]:
        idx = text.rfind(marker)
        if idx > len(text) // 3:  # only cut if marker is in the last 2/3
            text = text[:idx]
    return text.strip()


def parse_email(email: EmailInput) -> dict:
    """Parse and clean an incoming email, returning normalized data.

    Returns a dict with 'subject', 'body', and 'metadata' ready for the LLM.
    """
    subject = email.subject.strip()
    body = clean_text(email.body)

    if not body:
        raise ValueError("Email body is empty")

    metadata = None
    if email.metadata:
        metadata = email.metadata.model_dump(exclude_none=True)

    logger.info(
        "Parsed email: subject=%r, body_length=%d, has_metadata=%s",
        subject,
        len(body),
        metadata is not None,
    )

    return {"subject": subject, "body": body, "metadata": metadata}
