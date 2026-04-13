from __future__ import annotations

import json
import logging
import re

import anthropic
import openai
from google import genai
from google.genai import types as genai_types

from app.config import settings
from app.industry import get_industry_config

logger = logging.getLogger(__name__)


def _build_system_prompt() -> str:
    """Build the system prompt dynamically from the industry config."""
    industry = get_industry_config()

    lang_map = {"fr": "français", "en": "English", "es": "español", "de": "Deutsch"}
    lang_name = lang_map.get(industry.language, industry.language)

    company_ctx = ""
    if industry.company_name:
        company_ctx = f" ({industry.company_name})"

    rules_block = industry.response_rules_block()
    rules_section = ""
    if rules_block:
        rules_section = f"\n\nRègles de réponse par catégorie :\n{rules_block}"

    return f"""\
Tu es un agent de service client expert pour une entreprise du secteur \
"{industry.name}"{company_ctx}. {industry.description}.
Tu analyses les emails des clients et produis une réponse structurée en JSON.

Règles strictes :
- Ne jamais inventer de données client qui ne figurent pas dans l'email.
- Si une information est absente, laisser le champ vide ("") ou utiliser un \
placeholder comme {{{{valeur_manquante}}}}.
- La réponse suggérée doit être en {lang_name}, professionnelle et empathique.
- Si la demande est floue : poser des questions de clarification.{rules_section}

Catégories disponibles :
{industry.categories_description_block()}

Tu dois retourner UNIQUEMENT un objet JSON valide avec cette structure exacte :
{{
  "category": "{industry.categories_prompt_string()}",
  "confidence": 0.0-1.0,
  "sentiment": "positive | neutral | negative | angry",
  "urgency": "low | medium | high",
  "entities": {{
    {industry.entities_json_block()}
  }},
  "summary": "Résumé court de la demande",
  "suggested_reply": "Réponse email professionnelle en {lang_name}",
  "actions": ["Liste d'actions internes recommandées"]
}}

Pas de texte avant ou après le JSON. Uniquement le JSON."""


def _build_user_prompt(subject: str, body: str, metadata: dict | None = None) -> str:
    parts = []
    if subject:
        parts.append(f"Objet : {subject}")
    parts.append(f"Corps de l'email :\n{body}")
    if metadata:
        meta_str = ", ".join(f"{k}: {v}" for k, v in metadata.items() if v)
        if meta_str:
            parts.append(f"Métadonnées client : {meta_str}")
    return "\n\n".join(parts)


def _extract_json(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown fences."""
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)

    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    start = text.index("{")
    end = text.rindex("}") + 1
    return json.loads(text[start:end])


# --- Provider backends ---


def _call_anthropic(system_prompt: str, user_prompt: str) -> str:
    """Anthropic Claude API."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.model_name,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text


def _call_openai_compatible(system_prompt: str, user_prompt: str) -> str:
    """OpenAI ChatGPT + any OpenAI-compatible API.

    Works with: OpenAI, DeepSeek, Mistral, xAI/Grok, Groq, Together AI,
    Fireworks AI, Perplexity, Ollama, vLLM, llama.cpp, LM Studio.
    """
    kwargs = {}
    if settings.llm_base_url:
        kwargs["base_url"] = settings.llm_base_url
    client = openai.OpenAI(
        api_key=settings.openai_api_key or "not-needed",
        **kwargs,
    )
    response = client.chat.completions.create(
        model=settings.model_name,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def _call_google(system_prompt: str, user_prompt: str) -> str:
    """Google Gemini API."""
    client = genai.Client(api_key=settings.google_api_key)
    response = client.models.generate_content(
        model=settings.model_name,
        contents=user_prompt,
        config=genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=settings.max_tokens,
            temperature=settings.temperature,
        ),
    )
    return response.text


# --- Dispatcher ---

_PROVIDERS = {
    "anthropic": _call_anthropic,
    "openai": _call_openai_compatible,
    "google": _call_google,
}

_API_ERRORS = (anthropic.APIError, openai.APIError)


def call_llm(
    subject: str,
    body: str,
    metadata: dict | None = None,
    max_retries: int = 2,
) -> dict:
    """Call the configured LLM and return parsed JSON result.

    The system prompt is built dynamically from the loaded industry config.
    Retries on parse failures up to max_retries times.
    """
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(subject, body, metadata)
    provider = settings.llm_provider
    call_fn = _PROVIDERS[provider]

    last_error = None
    for attempt in range(1, max_retries + 1):
        logger.info("LLM call attempt %d/%d (provider=%s, model=%s)", attempt, max_retries, provider, settings.model_name)
        try:
            raw = call_fn(system_prompt, user_prompt)
            return _extract_json(raw)

        except (json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            logger.warning("JSON parse failed on attempt %d: %s", attempt, exc)
        except _API_ERRORS as exc:
            last_error = exc
            logger.error("API error on attempt %d: %s", attempt, exc)
            if attempt == max_retries:
                raise
        except Exception as exc:
            last_error = exc
            logger.error("Provider error on attempt %d: %s", attempt, exc)
            if attempt == max_retries:
                raise

    raise ValueError(f"Failed to get valid JSON after {max_retries} attempts: {last_error}")
