"""Integration tests that send sample emails through the full pipeline.

These tests call the actual LLM API. Set ANTHROPIC_API_KEY in .env to run them.
Skip with: pytest -m "not integration"
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.examples import (
    BILLING_EMAIL,
    BILLING_EXPECTED,
    COMPLAINT_EMAIL,
    COMPLAINT_EXPECTED,
    MOVE_EMAIL,
    MOVE_EXPECTED,
)

client = TestClient(app)


def _process(email_data: dict) -> dict:
    response = client.post("/process_email", json=email_data)
    assert response.status_code == 200, f"API returned {response.status_code}: {response.text}"
    return response.json()


# --- Unit tests (no LLM required) ---


class TestClassifierValidation:
    def test_valid_category(self):
        from app.classifier import validate_classification

        raw = {"category": "billing", "confidence": 0.9, "sentiment": "negative", "urgency": "high"}
        result = validate_classification(raw)
        assert result["category"] == "billing"

    def test_invalid_category_defaults_to_fallback(self):
        from app.classifier import validate_classification
        from app.industry import get_industry_config

        raw = {"category": "xyz", "confidence": 0.5, "sentiment": "neutral", "urgency": "low"}
        result = validate_classification(raw)
        assert result["category"] == get_industry_config().default_category

    def test_confidence_clamped(self):
        from app.classifier import validate_classification

        raw = {"category": "billing", "confidence": 1.5, "sentiment": "neutral", "urgency": "low"}
        result = validate_classification(raw)
        assert result["confidence"] == 1.0


class TestEntityExtraction:
    def test_extracts_present_fields(self):
        from app.entity_extractor import validate_entities

        raw = {"entities": {"customer_name": "Jean Dupont", "contract_id": "AB-123"}}
        entities = validate_entities(raw)
        assert entities["customer_name"] == "Jean Dupont"
        assert entities["contract_id"] == "AB-123"

    def test_handles_missing_entities(self):
        from app.entity_extractor import validate_entities

        entities = validate_entities({})
        # All configured entity fields should exist with empty values
        for value in entities.values():
            assert value == ""


class TestResponseValidation:
    def test_fallback_on_empty_reply(self):
        from app.response_generator import validate_response

        result = validate_response({"summary": "Test", "suggested_reply": ""})
        assert "conseiller" in result["suggested_reply"].lower()


class TestRulesEngine:
    def test_angry_escalation(self):
        from app.models import EmailProcessingResult
        from app.rules_engine import apply_business_rules

        result = EmailProcessingResult(
            category="complaint",
            confidence=0.9,
            sentiment="angry",
            urgency="low",
            entities={},
            summary="Test",
            suggested_reply="Nous sommes navrés pour ce désagrément.",
            actions=[],
        )
        result = apply_business_rules(result)
        assert result.urgency == "high"
        assert any("Escalader" in a for a in result.actions)

    def test_low_confidence_flagged(self):
        from app.models import EmailProcessingResult
        from app.rules_engine import apply_business_rules

        result = EmailProcessingResult(
            category="other",
            confidence=0.3,
            sentiment="neutral",
            urgency="low",
            entities={},
            summary="Test",
            suggested_reply="Bonjour.",
            actions=[],
        )
        result = apply_business_rules(result)
        assert result.requires_human_review is True


class TestEmailIngestion:
    def test_clean_signature(self):
        from app.email_ingestion import clean_text

        text = "Bonjour,\n\nMon message.\n\n--\nSignature"
        cleaned = clean_text(text)
        assert "Signature" not in cleaned

    def test_empty_body_raises(self):
        from app.email_ingestion import parse_email
        from app.models import EmailInput

        with pytest.raises(ValueError, match="empty"):
            parse_email(EmailInput(body=""))


class TestIndustryConfig:
    def test_loads_config(self):
        from app.industry import get_industry_config

        config = get_industry_config()
        assert config.name
        assert len(config.categories) > 0
        assert len(config.entities) > 0

    def test_category_names(self):
        from app.industry import get_industry_config

        config = get_industry_config()
        assert isinstance(config.category_names, set)
        assert config.default_category in config.category_names

    def test_prompt_generation(self):
        from app.industry import get_industry_config

        config = get_industry_config()
        assert "|" in config.categories_prompt_string()
        assert config.entities_json_block()


class TestConfigEndpoint:
    def test_config_returns_industry(self):
        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "categories" in data
        assert "entities" in data


# --- Integration tests (require LLM API) ---


@pytest.mark.integration
class TestBillingEmail:
    def test_billing_classification(self):
        result = _process(BILLING_EMAIL)
        assert result["category"] == BILLING_EXPECTED["category"]
        assert result["confidence"] >= BILLING_EXPECTED["confidence_min"]

    def test_billing_sentiment(self):
        result = _process(BILLING_EMAIL)
        assert result["sentiment"] in ("negative", "neutral")

    def test_billing_entities(self):
        result = _process(BILLING_EMAIL)
        entities = result["entities"]
        expected = BILLING_EXPECTED["entities"]
        assert expected["customer_name"] in entities["customer_name"]
        assert expected["contract_id"] in entities["contract_id"]
        assert expected["meter_number"] in entities["meter_number"]


@pytest.mark.integration
class TestComplaintEmail:
    def test_complaint_classification(self):
        result = _process(COMPLAINT_EMAIL)
        assert result["category"] == COMPLAINT_EXPECTED["category"]
        assert result["confidence"] >= COMPLAINT_EXPECTED["confidence_min"]

    def test_complaint_angry_sentiment(self):
        result = _process(COMPLAINT_EMAIL)
        assert result["sentiment"] == "angry"
        assert result["urgency"] == "high"

    def test_complaint_has_apology(self):
        result = _process(COMPLAINT_EMAIL)
        reply_lower = result["suggested_reply"].lower()
        assert any(
            m in reply_lower for m in ["excus", "désol", "navré"]
        ), "Reply should contain apology language"


@pytest.mark.integration
class TestMoveEmail:
    def test_move_classification(self):
        result = _process(MOVE_EMAIL)
        assert result["category"] == MOVE_EXPECTED["category"]
        assert result["confidence"] >= MOVE_EXPECTED["confidence_min"]

    def test_move_entities(self):
        result = _process(MOVE_EMAIL)
        entities = result["entities"]
        expected = MOVE_EXPECTED["entities"]
        assert expected["customer_name"] in entities["customer_name"]
        assert expected["contract_id"] in entities["contract_id"]

    def test_move_mentions_documents(self):
        result = _process(MOVE_EMAIL)
        reply_lower = result["suggested_reply"].lower()
        assert any(
            m in reply_lower for m in ["justificatif", "document", "pièce"]
        ), "Move reply should mention required documents"


@pytest.mark.integration
class TestHealthEndpoint:
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "industry" in data
