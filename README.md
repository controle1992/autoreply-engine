# AutoReply Engine

AI-powered customer service email processing that works with **any industry** and **any LLM provider**.

Configure your business sector via a YAML file, plug in your preferred AI provider, and deploy.

**Supported providers:** Anthropic Claude, OpenAI ChatGPT, Google Gemini, DeepSeek, Mistral, xAI (Grok), Groq, Together AI, Fireworks AI, Perplexity, Ollama, vLLM, llama.cpp, LM Studio — and any OpenAI-compatible API.

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
    - [Quick Reference Table](#quick-reference-table)
    - [Anthropic Claude](#anthropic-claude)
    - [OpenAI ChatGPT](#openai-chatgpt)
    - [Google Gemini](#google-gemini)
    - [DeepSeek](#deepseek)
    - [Mistral AI](#mistral-ai)
    - [xAI (Grok)](#xai-grok)
    - [Groq](#groq)
    - [Together AI](#together-ai)
    - [Fireworks AI](#fireworks-ai)
    - [Perplexity](#perplexity)
    - [Ollama (local)](#ollama-local)
    - [vLLM (local)](#vllm-local)
    - [llama.cpp (local)](#llamacpp-local)
    - [LM Studio (local)](#lm-studio-local)
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
- An LLM backend — any one of the [supported providers](#llm-provider-setup)

## Installation

```bash
git clone <repo-url> && cd autoreply-engine
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` to set your provider, API key, and industry config.

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INDUSTRY_CONFIG` | No | `configs/utilities.yaml` | Path to industry YAML config file |
| `LLM_PROVIDER` | No | `anthropic` | `"anthropic"`, `"openai"`, or `"google"` |
| `LLM_BASE_URL` | For non-OpenAI compatible APIs | — | Base URL override (see provider table) |
| `ANTHROPIC_API_KEY` | When provider=anthropic | — | Anthropic API key |
| `OPENAI_API_KEY` | When provider=openai | — | API key (works for all OpenAI-compatible providers) |
| `GOOGLE_API_KEY` | When provider=google | — | Google Gemini API key |
| `MODEL_NAME` | No | `claude-sonnet-4-20250514` | Model identifier (varies by provider) |
| `MAX_TOKENS` | No | `4096` | Maximum tokens in LLM response |
| `TEMPERATURE` | No | `0.2` | Sampling temperature (lower = more deterministic) |
| `CONFIDENCE_THRESHOLD` | No | `0.6` | Results below this are flagged for human review |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Industry Configuration

The industry is defined by a single YAML file. To switch industries, change `INDUSTRY_CONFIG` in `.env`:

```env
INDUSTRY_CONFIG=configs/utilities.yaml     # Water, electricity, gas
INDUSTRY_CONFIG=configs/ecommerce.yaml     # Online retail
INDUSTRY_CONFIG=configs/healthcare.yaml    # Medical clinics
INDUSTRY_CONFIG=configs/my_client.yaml     # Your own
```

#### Included Configs

| File | Industry | Categories | Entities |
|------|----------|------------|----------|
| `configs/utilities.yaml` | Water, electricity, gas | billing, complaint, move, contract, technical_issue, other | customer_name, contract_id, address, date, amount, meter_number |
| `configs/ecommerce.yaml` | Online retail | order_issue, return_refund, delivery, product_question, account, complaint, other | customer_name, order_number, product_name, address, date, amount, tracking_number |
| `configs/healthcare.yaml` | Medical clinics | appointment, results, billing, prescription, complaint, insurance, other | patient_name, patient_id, date_of_birth, appointment_date, doctor_name, insurance_number, amount |

#### Creating Your Own Industry Config

Create a new YAML file in `configs/`. Example for a real estate agency:

```yaml
name: "Agence Immobilière"
description: "Agence de location et vente de biens immobiliers"
language: "fr"
company_name: "ImmoPlus"

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
```

Then set `INDUSTRY_CONFIG=configs/realestate.yaml` in `.env`.

#### Config Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Industry display name |
| `description` | string | Yes | One-line description (used in LLM system prompt) |
| `language` | string | No | Response language: `fr`, `en`, `es`, `de` (default: `fr`) |
| `company_name` | string | No | Client's company name (used in prompt context) |
| `categories` | list | Yes | `{name, description}` objects |
| `entities` | list | Yes | Entity field names to extract (snake_case) |
| `response_rules` | list | No | Per-category reply rules (see below) |

**Response rules:**

| Field | Type | Description |
|-------|------|-------------|
| `category` | string | Which category this rule applies to |
| `instruction` | string | Instruction added to the LLM prompt |
| `reply_must_contain` | list | Keywords to check in reply (case-insensitive) |
| `fallback_prefix` | string | Prepended if keywords missing |
| `fallback_suffix` | string | Appended if keywords missing |
| `ensure_action` | string | Action added if not already present |

---

### LLM Provider Setup

The engine uses three provider modes set via `LLM_PROVIDER`:

| Mode | Value | Covers |
|------|-------|--------|
| Anthropic SDK | `anthropic` | Claude |
| OpenAI SDK | `openai` | ChatGPT, DeepSeek, Mistral, xAI, Groq, Together, Fireworks, Perplexity, Ollama, vLLM, llama.cpp, LM Studio |
| Google SDK | `google` | Gemini |

The `openai` mode works with **any service** that exposes the OpenAI-compatible `/v1/chat/completions` endpoint. Just set the right `LLM_BASE_URL` and `OPENAI_API_KEY`.

#### Quick Reference Table

Copy-paste the `.env` block for your provider:

| Provider | `LLM_PROVIDER` | `LLM_BASE_URL` | API Key Variable | Example Model |
|----------|----------------|-----------------|------------------|---------------|
| Anthropic Claude | `anthropic` | _(not used)_ | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |
| OpenAI ChatGPT | `openai` | _(leave empty)_ | `OPENAI_API_KEY` | `gpt-4o` |
| Google Gemini | `google` | _(not used)_ | `GOOGLE_API_KEY` | `gemini-2.5-flash` |
| DeepSeek | `openai` | `https://api.deepseek.com/v1` | `OPENAI_API_KEY` | `deepseek-chat` |
| Mistral AI | `openai` | `https://api.mistral.ai/v1` | `OPENAI_API_KEY` | `mistral-large-latest` |
| xAI (Grok) | `openai` | `https://api.x.ai/v1` | `OPENAI_API_KEY` | `grok-3` |
| Groq | `openai` | `https://api.groq.com/openai/v1` | `OPENAI_API_KEY` | `llama-3.3-70b-versatile` |
| Together AI | `openai` | `https://api.together.xyz/v1` | `OPENAI_API_KEY` | `meta-llama/Llama-3.1-70B-Instruct-Turbo` |
| Fireworks AI | `openai` | `https://api.fireworks.ai/inference/v1` | `OPENAI_API_KEY` | `accounts/fireworks/models/llama-v3p1-70b-instruct` |
| Perplexity | `openai` | `https://api.perplexity.ai` | `OPENAI_API_KEY` | `sonar-pro` |
| Ollama | `openai` | `http://localhost:11434/v1` | `OPENAI_API_KEY=not-needed` | `llama3.1:8b` |
| vLLM | `openai` | `http://localhost:8000/v1` | `OPENAI_API_KEY=not-needed` | `meta-llama/Llama-3.1-8B-Instruct` |
| llama.cpp | `openai` | `http://localhost:8080/v1` | `OPENAI_API_KEY=not-needed` | `llama-3.1-8b-instruct` |
| LM Studio | `openai` | `http://localhost:1234/v1` | `OPENAI_API_KEY=not-needed` | _(loaded model)_ |

---

#### Anthropic Claude

Get an API key from [console.anthropic.com](https://console.anthropic.com/).

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
MODEL_NAME=claude-sonnet-4-20250514
```

| Model | ID |
|-------|----|
| Claude Opus 4.6 | `claude-opus-4-6-20250415` |
| Claude Sonnet 4.6 | `claude-sonnet-4-6-20250415` |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` |

---

#### OpenAI ChatGPT

Get an API key from [platform.openai.com](https://platform.openai.com/). No `LLM_BASE_URL` needed — defaults to OpenAI's API.

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxx
MODEL_NAME=gpt-4o
```

| Model | ID | Notes |
|-------|----|-------|
| GPT-4o | `gpt-4o` | Best quality/speed balance |
| GPT-4o mini | `gpt-4o-mini` | Faster, cheaper |
| GPT-4.1 | `gpt-4.1` | Latest |
| o3-mini | `o3-mini` | Reasoning model |

---

#### Google Gemini

Get an API key from [aistudio.google.com](https://aistudio.google.com/apikey).

```env
LLM_PROVIDER=google
GOOGLE_API_KEY=AIzaSyxxxxx
MODEL_NAME=gemini-2.5-flash
```

| Model | ID | Notes |
|-------|----|-------|
| Gemini 2.5 Flash | `gemini-2.5-flash` | Fast, cost-effective |
| Gemini 2.5 Pro | `gemini-2.5-pro` | Higher quality |
| Gemini 2.0 Flash | `gemini-2.0-flash` | Previous gen, still solid |

---

#### DeepSeek

Get an API key from [platform.deepseek.com](https://platform.deepseek.com/).

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.deepseek.com/v1
OPENAI_API_KEY=sk-xxxxx
MODEL_NAME=deepseek-chat
```

| Model | ID | Notes |
|-------|----|-------|
| DeepSeek-V3 | `deepseek-chat` | General purpose |
| DeepSeek-R1 | `deepseek-reasoner` | Reasoning model |

---

#### Mistral AI

Get an API key from [console.mistral.ai](https://console.mistral.ai/).

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.mistral.ai/v1
OPENAI_API_KEY=xxxxx
MODEL_NAME=mistral-large-latest
```

| Model | ID | Notes |
|-------|----|-------|
| Mistral Large | `mistral-large-latest` | Best quality |
| Mistral Small | `mistral-small-latest` | Faster, cheaper |
| Codestral | `codestral-latest` | Code-focused |

---

#### xAI (Grok)

Get an API key from [console.x.ai](https://console.x.ai/).

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.x.ai/v1
OPENAI_API_KEY=xai-xxxxx
MODEL_NAME=grok-3
```

| Model | ID |
|-------|----|
| Grok 3 | `grok-3` |
| Grok 3 Mini | `grok-3-mini` |

---

#### Groq

Get an API key from [console.groq.com](https://console.groq.com/). Known for very fast inference.

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY=gsk_xxxxx
MODEL_NAME=llama-3.3-70b-versatile
```

| Model | ID | Notes |
|-------|----|-------|
| Llama 3.3 70B | `llama-3.3-70b-versatile` | Best quality on Groq |
| Mixtral 8x7B | `mixtral-8x7b-32768` | Fast, 32k context |

---

#### Together AI

Get an API key from [api.together.xyz](https://api.together.xyz/).

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.together.xyz/v1
OPENAI_API_KEY=xxxxx
MODEL_NAME=meta-llama/Llama-3.1-70B-Instruct-Turbo
```

---

#### Fireworks AI

Get an API key from [fireworks.ai](https://fireworks.ai/).

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.fireworks.ai/inference/v1
OPENAI_API_KEY=xxxxx
MODEL_NAME=accounts/fireworks/models/llama-v3p1-70b-instruct
```

---

#### Perplexity

Get an API key from [perplexity.ai](https://www.perplexity.ai/).

```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.perplexity.ai
OPENAI_API_KEY=pplx-xxxxx
MODEL_NAME=sonar-pro
```

| Model | ID | Notes |
|-------|----|-------|
| Sonar Pro | `sonar-pro` | With search grounding |
| Sonar | `sonar` | Lighter, faster |

---

#### Ollama (local)

Run open-source models locally. Install from [ollama.com](https://ollama.com/).

```bash
ollama pull llama3.1:8b
```

```env
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=not-needed
MODEL_NAME=llama3.1:8b
```

| Model | Command | Notes |
|-------|---------|-------|
| Llama 3.1 8B | `ollama pull llama3.1:8b` | Good balance |
| Llama 3.1 70B | `ollama pull llama3.1:70b` | Best quality, ~40GB RAM |
| Mistral 7B | `ollama pull mistral` | Fast |
| Qwen 2.5 14B | `ollama pull qwen2.5:14b` | Strong multilingual |
| Mixtral 8x7B | `ollama pull mixtral` | Good quality |

---

#### vLLM (local)

High-throughput serving. See [docs.vllm.ai](https://docs.vllm.ai/).

```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8000
```

```env
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:8000/v1
OPENAI_API_KEY=not-needed
MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct
```

---

#### llama.cpp (local)

Lightweight C++ inference. See [github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp).

```bash
llama-server -m models/llama-3.1-8b-instruct.gguf --port 8080
```

```env
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:8080/v1
OPENAI_API_KEY=not-needed
MODEL_NAME=llama-3.1-8b-instruct
```

---

#### LM Studio (local)

Desktop app with GUI. Download from [lmstudio.ai](https://lmstudio.ai/).

1. Download a model in the app
2. Start the local server from the "Local Server" tab

```env
LLM_PROVIDER=openai
LLM_BASE_URL=http://localhost:1234/v1
OPENAI_API_KEY=not-needed
MODEL_NAME=loaded-model-name
```

---

> **Any other provider** that exposes an OpenAI-compatible `/v1/chat/completions` endpoint will work. Set `LLM_PROVIDER=openai`, point `LLM_BASE_URL` to it, and set `OPENAI_API_KEY` to the provider's key.

## Running the Server

```bash
# Development
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Interactive docs at `http://localhost:8000/docs`.

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
    "body": "Bonjour, ma commande #ORD-4421 n'est toujours pas arrivée.",
})
result = response.json()
print(result["category"])         # "delivery" (with ecommerce config)
print(result["suggested_reply"])  # French reply
print(result["entities"])         # {"order_number": "ORD-4421", ...}
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
| `category` | string | From the industry config categories |
| `confidence` | float | 0.0 to 1.0 |
| `sentiment` | string | `positive`, `neutral`, `negative`, or `angry` |
| `urgency` | string | `low`, `medium`, or `high` |
| `entities` | object | Extracted data (fields from industry config) |
| `summary` | string | Short summary of the request |
| `suggested_reply` | string | Reply draft in configured language |
| `actions` | array | Recommended internal actions |
| `requires_human_review` | bool | `true` if flagged by rules |
| `review_reason` | string\|null | Why human review is needed |

**Errors:** `422` (invalid input), `502` (LLM failure), `500` (parse failure).

### GET /config

Returns the loaded industry configuration.

```bash
curl http://localhost:8000/config
```

### GET /health

```bash
curl http://localhost:8000/health
# {"status": "ok", "industry": "Services Publics"}
```

## Business Rules

**Universal rules** (always active):

| Rule | Trigger | Action |
|------|---------|--------|
| Low confidence | `confidence < CONFIDENCE_THRESHOLD` | Flag for human review |
| Angry customer | `sentiment = "angry"` | Escalate urgency to HIGH |

**Industry-specific rules** (from YAML `response_rules`): check reply keywords, prepend/append fallback text, ensure actions are present.

## Testing

```bash
python3 -m pytest tests/ -v -m "not integration"   # Unit tests (no API key)
python3 -m pytest tests/ -v -m integration          # Integration tests
python3 -m pytest tests/ -v                          # All
```

## Sample Emails

Three test emails in `tests/examples.py` (utilities): billing issue, angry complaint, move request.

## Project Structure

```
autoreply-engine/
├── app/
│   ├── main.py               # FastAPI app, pipeline
│   ├── config.py              # Settings from .env
│   ├── industry.py            # YAML industry config loader
│   ├── models.py              # Pydantic schemas
│   ├── llm_client.py          # Multi-provider LLM abstraction
│   ├── email_ingestion.py     # Email parsing and cleaning
│   ├── classifier.py          # Classification validation
│   ├── entity_extractor.py    # Entity validation
│   ├── response_generator.py  # Reply validation
│   └── rules_engine.py        # Business rules engine
├── configs/
│   ├── utilities.yaml
│   ├── ecommerce.yaml
│   └── healthcare.yaml
├── tests/
│   ├── examples.py
│   └── test_examples.py
├── requirements.txt
├── .env.example
├── pytest.ini
└── README.md
```

## Troubleshooting

**"API key not set" / 401 errors**
- Ensure the correct key variable is set for your provider (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GOOGLE_API_KEY`)
- For local models: set `OPENAI_API_KEY=not-needed`

**"Connection refused"**
- For local models: ensure the server is running and the port matches `LLM_BASE_URL`
- Test: `curl http://localhost:11434/v1/models`

**JSON parse errors**
- Smaller models may struggle with structured JSON. Try lower `TEMPERATURE` (0.1), a larger model, or more `MAX_TOKENS`
- The engine retries automatically on parse failure

**"requires_human_review" on every request**
- Lower `CONFIDENCE_THRESHOLD` (e.g., 0.4 for smaller models)

**Wrong categories**
- Make sure category descriptions in your YAML are clear and distinct
