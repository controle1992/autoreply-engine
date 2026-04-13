# AutoReply Engine

AI-powered customer service email processing that works with **any industry**. Configure your business sector, categories, entities, and reply rules via a simple YAML file — then deploy for any client.

Supports Anthropic Claude and any local/remote model via OpenAI-compatible APIs (Ollama, vLLM, llama.cpp, LM Studio).

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Industry Configuration](#industry-configuration)
    - [Included Configs](#included-configs)
    - [Creating Your Own Industry Config](#creating-your-own-industry-config)
    - [Config Reference](#config-reference)
  - [LLM Provider Setup](#llm-provider-setup)
    - [Anthropic Claude](#option-1-anthropic-claude-api)
    - [Ollama (local Llama, Mistral, etc.)](#option-2-ollama-local)
    - [vLLM](#option-3-vllm)
    - [llama.cpp server](#option-4-llamacpp-server)
    - [LM Studio](#option-5-lm-studio)
- [Running the Server](#running-the-server)
- [API Reference](#api-reference)
  - [POST /process_email](#post-process_email)
  - [GET /config](#get-config)
  - [GET /health](#get-health)
- [Business Rules](#business-rules)
- [Testing](#testing)
- [Sample Emails](#sample-emails)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

## Architecture

```
Email ─► Parse & Clean ─► LLM (single call) ─► Validate ─► Business Rules ─► Structured JSON
                               ▲
                    Industry YAML config
                  (categories, entities, rules)
```

The system prompt, categories, entity fields, and reply rules are all generated dynamically from a YAML config file. Switch industries by changing one line in `.env`.

## Prerequisites

- Python 3.10+
- An LLM backend — one of:
  - Anthropic API key, **or**
  - A locally running model server (Ollama, vLLM, llama.cpp, LM Studio)

## Installation

```bash
# Clone the repository
git clone <repo-url> && cd autoreply-engine

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
```

Then edit `.env` to set your API key and choose an industry config.

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INDUSTRY_CONFIG` | No | `configs/utilities.yaml` | Path to industry YAML config file |
| `LLM_PROVIDER` | No | `anthropic` | LLM backend: `"anthropic"` or `"openai"` |
| `LLM_BASE_URL` | When provider=openai | — | Base URL of the OpenAI-compatible API |
| `ANTHROPIC_API_KEY` | When provider=anthropic | — | Anthropic API key |
| `OPENAI_API_KEY` | No | `not-needed` | API key for OpenAI-compatible server |
| `MODEL_NAME` | No | `claude-sonnet-4-20250514` | Model identifier (varies by provider) |
| `MAX_TOKENS` | No | `4096` | Maximum tokens in LLM response |
| `TEMPERATURE` | No | `0.2` | Sampling temperature (lower = more deterministic) |
| `CONFIDENCE_THRESHOLD` | No | `0.6` | Results below this confidence are flagged for human review |
| `LOG_LEVEL` | No | `INFO` | Python log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Industry Configuration

The industry is defined by a single YAML file. To switch industries, change `INDUSTRY_CONFIG` in `.env`:

```env
# Utilities (water, electricity, gas)
INDUSTRY_CONFIG=configs/utilities.yaml

# E-commerce (orders, returns, shipping)
INDUSTRY_CONFIG=configs/ecommerce.yaml

# Healthcare (appointments, prescriptions, billing)
INDUSTRY_CONFIG=configs/healthcare.yaml

# Your own custom config
INDUSTRY_CONFIG=configs/my_client.yaml
```

#### Included Configs

| File | Industry | Categories | Entities |
|------|----------|------------|----------|
| `configs/utilities.yaml` | Water, electricity, gas | billing, complaint, move, contract, technical_issue, other | customer_name, contract_id, address, date, amount, meter_number |
| `configs/ecommerce.yaml` | Online retail | order_issue, return_refund, delivery, product_question, account, complaint, other | customer_name, order_number, product_name, address, date, amount, tracking_number |
| `configs/healthcare.yaml` | Medical clinics | appointment, results, billing, prescription, complaint, insurance, other | patient_name, patient_id, date_of_birth, appointment_date, doctor_name, insurance_number, amount |

#### Creating Your Own Industry Config

Create a new YAML file in `configs/`. Here's a minimal example for a real estate agency:

```yaml
name: "Agence Immobilière"
description: "Agence de location et vente de biens immobiliers"
language: "fr"
company_name: "ImmoPlus"  # optional, shown in replies

categories:
  - name: rental_inquiry
    description: "Demande d'information sur un bien à louer"
  - name: purchase_inquiry
    description: "Demande d'information sur un bien à vendre"
  - name: maintenance
    description: "Signalement de problème ou demande de réparation"
  - name: lease
    description: "Questions sur le bail, renouvellement, résiliation"
  - name: complaint
    description: "Insatisfaction, litige"
  - name: other
    description: "Demandes générales"

entities:
  - tenant_name
  - property_address
  - property_reference
  - lease_number
  - date
  - amount

response_rules:
  - category: complaint
    instruction: "S'excuser et proposer un rendez-vous"
    reply_must_contain: ["excus", "désol", "navré"]
    fallback_prefix: "Nous sommes sincèrement désolés pour cette situation.\n\n"

  - category: maintenance
    instruction: "Confirmer la prise en compte et donner un délai d'intervention"
    ensure_action: "Créer un ticket d'intervention maintenance"

  - category: lease
    instruction: "Rappeler les termes du bail et les démarches à suivre"
    ensure_action: "Vérifier le dossier locataire"
```

Then set `INDUSTRY_CONFIG=configs/realestate.yaml` in `.env`.

#### Config Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Industry display name (shown in API docs and /health) |
| `description` | string | Yes | One-line description used in the LLM system prompt |
| `language` | string | No | Response language code: `fr`, `en`, `es`, `de` (default: `fr`) |
| `company_name` | string | No | Your client's company name (used in prompt context) |
| `categories` | list | Yes | List of `{name, description}` objects |
| `categories[].name` | string | Yes | Machine-readable category ID (lowercase, snake_case) |
| `categories[].description` | string | Yes | Human description, included in LLM prompt |
| `entities` | list | Yes | List of entity field names to extract (snake_case strings) |
| `response_rules` | list | No | Per-category reply rules (see below) |

**Response rules fields:**

| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Which category this rule applies to |
| `instruction` | string | Instruction added to the LLM prompt for this category |
| `reply_must_contain` | list | Substrings to check for in the reply (case-insensitive) |
| `fallback_prefix` | string | Prepended to reply if `reply_must_contain` check fails |
| `fallback_suffix` | string | Appended to reply if `reply_must_contain` check fails |
| `ensure_action` | string | Action added to the actions list if not already present |

### LLM Provider Setup

The engine supports two provider modes. Set `LLM_PROVIDER` in your `.env` to switch.

---

#### Option 1: Anthropic Claude API

Best quality. Requires an API key from [console.anthropic.com](https://console.anthropic.com/).

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
MODEL_NAME=claude-sonnet-4-20250514
```

Available Anthropic models:
| Model | ID |
|-------|----|
| Claude Opus 4.6 | `claude-opus-4-6-20250415` |
| Claude Sonnet 4.6 | `claude-sonnet-4-6-20250415` |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` |

---

#### Option 2: Ollama (local)

Run open-source models locally. Install from [ollama.com](https://ollama.com/).

```bash
ollama pull llama3.1:8b
```

```env
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:11434/v1
MODEL_NAME=llama3.1:8b
```

Recommended models:

| Model | Command | Notes |
|-------|---------|-------|
| Llama 3.1 8B | `ollama pull llama3.1:8b` | Good balance of speed and quality |
| Llama 3.1 70B | `ollama pull llama3.1:70b` | Best quality, needs ~40GB RAM |
| Mistral 7B | `ollama pull mistral` | Fast, decent French support |
| Qwen 2.5 14B | `ollama pull qwen2.5:14b` | Strong multilingual performance |
| Mixtral 8x7B | `ollama pull mixtral` | Good quality, moderate resources |

---

#### Option 3: vLLM

High-throughput serving. See [docs.vllm.ai](https://docs.vllm.ai/).

```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8000
```

```env
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:8000/v1
MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct
```

---

#### Option 4: llama.cpp server

Lightweight C++ inference. See [github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp).

```bash
llama-server -m models/llama-3.1-8b-instruct.gguf --port 8080
```

```env
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:8080/v1
MODEL_NAME=llama-3.1-8b-instruct
```

---

#### Option 5: LM Studio

Desktop app with GUI. Download from [lmstudio.ai](https://lmstudio.ai/).

1. Download a model in the app
2. Go to the "Local Server" tab and start the server

```env
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:1234/v1
MODEL_NAME=loaded-model-name
```

---

> **Any server** that exposes the OpenAI-compatible `/v1/chat/completions` endpoint will work. Just set `LLM_PROVIDER=openai` and point `LLM_BASE_URL` to it.

## Running the Server

```bash
# Development (auto-reload on code changes)
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Custom port
uvicorn app.main:app --reload --port 3000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API Reference

### POST /process_email

Process a customer email and return structured analysis with a suggested reply.

**Request body:**

```json
{
  "subject": "Erreur sur ma facture",
  "body": "Bonjour, ma facture de mars indique 347€ au lieu de 85€. Mon contrat: EL-2024-78542. Merci, Jean Martin",
  "metadata": {
    "customer_id": "CUS-12345",
    "contract_id": "EL-2024-78542",
    "account_type": "residential"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `subject` | string | No | Email subject line |
| `body` | string | **Yes** | Email body text |
| `metadata` | object | No | Optional customer context |
| `metadata.customer_id` | string | No | Customer ID from your system |
| `metadata.contract_id` | string | No | Known contract ID |
| `metadata.account_type` | string | No | Account type |

**cURL example:**

```bash
curl -X POST http://localhost:8000/process_email \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Erreur sur ma facture",
    "body": "Bonjour, ma facture de mars indique 347€ au lieu de 85€. Mon contrat: EL-2024-78542. Merci, Jean Martin"
  }'
```

**Python example:**

```python
import httpx

response = httpx.post("http://localhost:8000/process_email", json={
    "subject": "Problème de livraison",
    "body": "Bonjour, ma commande #ORD-4421 n'est toujours pas arrivée. Merci de vérifier.",
})
result = response.json()
print(result["category"])         # "delivery" (with ecommerce config)
print(result["suggested_reply"])  # French reply
print(result["entities"])         # {"customer_name": "", "order_number": "ORD-4421", ...}
```

**Response body:**

```json
{
  "category": "billing",
  "confidence": 0.95,
  "sentiment": "negative",
  "urgency": "medium",
  "entities": {
    "customer_name": "Jean Martin",
    "contract_id": "EL-2024-78542",
    "address": "",
    "date": "mars",
    "amount": "347€",
    "meter_number": ""
  },
  "summary": "Client signale un montant de facture anormalement élevé",
  "suggested_reply": "Madame, Monsieur, ...",
  "actions": [
    "Vérifier le relevé de compteur",
    "Vérifier l'historique de facturation du client"
  ],
  "requires_human_review": false,
  "review_reason": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `category` | string | One of the categories defined in the industry config |
| `confidence` | float | 0.0 to 1.0 |
| `sentiment` | string | `positive`, `neutral`, `negative`, or `angry` |
| `urgency` | string | `low`, `medium`, or `high` |
| `entities` | object | Key-value map of extracted entities (fields depend on industry config) |
| `summary` | string | Short summary of the customer's request |
| `suggested_reply` | string | Professional reply draft in the configured language |
| `actions` | array | Recommended internal actions |
| `requires_human_review` | bool | `true` if flagged by rules engine |
| `review_reason` | string | Why human review is needed (null if not needed) |

**Error responses:**

| Status | Cause |
|--------|-------|
| 422 | Empty email body or invalid input |
| 502 | LLM API call failed |
| 500 | Failed to parse LLM output after retries |

### GET /config

Returns the current industry configuration (categories, entities, language).

```bash
curl http://localhost:8000/config
```

```json
{
  "name": "Services Publics",
  "description": "Entreprise de services publics (eau, électricité, gaz)",
  "language": "fr",
  "categories": [
    {"name": "billing", "description": "Erreurs de facturation, ..."},
    {"name": "complaint", "description": "Qualité de service, ..."}
  ],
  "entities": ["customer_name", "contract_id", "address", "date", "amount", "meter_number"]
}
```

### GET /health

```bash
curl http://localhost:8000/health
```

Returns `{"status": "ok", "industry": "Services Publics"}`.

## Business Rules

The rules engine applies two layers of deterministic logic after the LLM response:

**Universal rules** (always active):

| Rule | Trigger | Action |
|------|---------|--------|
| Low confidence | `confidence < CONFIDENCE_THRESHOLD` | Flag `requires_human_review = true`, add escalation action |
| Angry customer | `sentiment = "angry"` | Override `urgency` to `"high"`, add escalation action |

**Industry-specific rules** (from the YAML config `response_rules`):

Each rule can:
- Check that the reply contains specific keywords (`reply_must_contain`)
- Prepend/append fallback text if keywords are missing (`fallback_prefix`/`fallback_suffix`)
- Ensure a specific action is in the actions list (`ensure_action`)

Example: the utilities config ensures complaint replies contain an apology, move replies mention required documents, and billing results include a billing check action.

## Testing

```bash
# Unit tests only (no API key needed) — 14 tests
python3 -m pytest tests/ -v -m "not integration"

# Integration tests (requires a working LLM configured in .env)
python3 -m pytest tests/ -v -m integration

# All tests
python3 -m pytest tests/ -v
```

## Sample Emails

Three test emails are included in `tests/examples.py` (utilities sector):

1. **Billing issue** — Customer reports an abnormally high electricity bill. Includes contract ID, meter number, address.
2. **Complaint** — Angry customer about unannounced water outage. Triggers angry sentiment detection and urgency escalation.
3. **Move request** — Customer moving within the same city, wants to transfer gas contract. Triggers document checklist in the reply.

## Project Structure

```
autoreply-engine/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app, pipeline orchestration
│   ├── config.py              # Pydantic settings from .env
│   ├── industry.py            # YAML industry config loader
│   ├── models.py              # Input/output Pydantic schemas
│   ├── llm_client.py          # LLM abstraction (Anthropic + OpenAI-compatible)
│   ├── email_ingestion.py     # Email parsing, signature removal, text cleaning
│   ├── classifier.py          # Classification validation against config categories
│   ├── entity_extractor.py    # Entity validation using config entity fields
│   ├── response_generator.py  # Reply validation with fallbacks
│   └── rules_engine.py        # Universal + config-driven business rules
├── configs/
│   ├── utilities.yaml         # Water, electricity, gas
│   ├── ecommerce.yaml         # Online retail
│   └── healthcare.yaml        # Medical clinics
├── tests/
│   ├── __init__.py
│   ├── examples.py            # 3 sample emails with expected outputs
│   └── test_examples.py       # 14 unit tests + 10 integration tests
├── requirements.txt
├── .env.example
├── pytest.ini
└── README.md
```

## Troubleshooting

**"Industry config not found"**
- Check that `INDUSTRY_CONFIG` in `.env` points to an existing YAML file
- Paths are relative to the working directory where you start the server

**"API key not set" / 401 errors**
- For Anthropic: ensure `ANTHROPIC_API_KEY` is set correctly in `.env`
- For local models: set `OPENAI_API_KEY=not-needed`

**"Connection refused" with local models**
- Make sure your model server is running before starting the app
- Verify the port matches `LLM_BASE_URL`
- Test directly: `curl http://localhost:11434/v1/models`

**JSON parse errors / bad output from local models**
- Smaller models (7B) may struggle with structured JSON output. Try:
  - Lowering `TEMPERATURE` to `0.1`
  - Using a larger model (14B+)
  - Increasing `MAX_TOKENS`
- The engine retries once automatically on parse failure

**Slow responses with local models**
- Ensure GPU acceleration is enabled
- Use a smaller/quantized model for faster inference
- Reduce `MAX_TOKENS` if replies are longer than needed

**"requires_human_review" on every request**
- The model may be consistently reporting low confidence. Adjust `CONFIDENCE_THRESHOLD` in `.env`
- Smaller local models tend to produce lower confidence scores — try lowering the threshold to 0.4

**Wrong categories returned**
- Verify your YAML config categories have clear, distinct descriptions
- The LLM uses the description text to distinguish between categories — vague descriptions lead to misclassification
