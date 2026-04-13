from __future__ import annotations

import logging
import time

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from app.classifier import validate_classification
from app.config import settings
from app.email_ingestion import parse_email
from app.entity_extractor import validate_entities
from app.industry import get_industry_config
from app.llm_client import call_llm
from app.models import EmailInput, EmailProcessingResult
from app.response_generator import validate_response
from app.rules_engine import apply_business_rules

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Load industry config at startup
industry = get_industry_config()

app = FastAPI(
    title="AutoReply Engine",
    description=f"AI-powered customer service email processing — {industry.name}",
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "industry": industry.name}


@app.get("/config")
def get_config():
    """Return the current industry configuration."""
    return {
        "name": industry.name,
        "description": industry.description,
        "language": industry.language,
        "categories": [{"name": c.name, "description": c.description} for c in industry.categories],
        "entities": industry.entities,
    }


@app.post("/process_email", response_model=EmailProcessingResult)
def process_email(email: EmailInput):
    """Process a customer email and return structured analysis + suggested reply.

    Pipeline:
    1. Parse & clean the email
    2. Call LLM for classification, extraction, and response
    3. Validate each component of the LLM output
    4. Apply business rules
    5. Return structured result
    """
    start = time.time()

    # 1. Parse & clean
    try:
        parsed = parse_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # 2. Call LLM
    try:
        raw_result = call_llm(
            subject=parsed["subject"],
            body=parsed["body"],
            metadata=parsed["metadata"],
        )
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="AI processing failed. Please try again later.",
        )

    # 3. Validate each component
    classification = validate_classification(raw_result)
    entities = validate_entities(raw_result)
    response_data = validate_response(raw_result)

    # 4. Assemble result
    try:
        result = EmailProcessingResult(
            category=classification["category"],
            confidence=classification["confidence"],
            sentiment=classification["sentiment"],
            urgency=classification["urgency"],
            entities=entities,
            summary=response_data["summary"],
            suggested_reply=response_data["suggested_reply"],
            actions=response_data["actions"],
        )
    except ValidationError as exc:
        logger.error("Result validation failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to build structured result from AI output.",
        )

    # 5. Apply business rules
    result = apply_business_rules(result)

    elapsed = time.time() - start
    logger.info(
        "Processed email in %.2fs: category=%s confidence=%.2f urgency=%s review=%s",
        elapsed,
        result.category,
        result.confidence,
        result.urgency,
        result.requires_human_review,
    )

    return result
