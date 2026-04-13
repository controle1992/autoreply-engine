from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --- Enums (sentiment and urgency are universal) ---

class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    ANGRY = "angry"


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# --- Input Models ---

class CustomerMetadata(BaseModel):
    """Optional metadata about the customer."""
    customer_id: Optional[str] = None
    contract_id: Optional[str] = None
    account_type: Optional[str] = None


class EmailInput(BaseModel):
    """Incoming customer email to process."""
    subject: str = ""
    body: str
    metadata: Optional[CustomerMetadata] = None


# --- Output Models ---

class EmailProcessingResult(BaseModel):
    """Full structured result from processing a customer email."""
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    sentiment: Sentiment
    urgency: Urgency
    entities: dict[str, str] = Field(default_factory=dict)
    summary: str
    suggested_reply: str
    actions: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
    review_reason: Optional[str] = None
