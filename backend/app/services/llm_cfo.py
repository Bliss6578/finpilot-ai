from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

import httpx

from app.config import Settings


logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\s-]?){8,15}(?!\d)")
NUMBER_PATTERN = re.compile(r"(?<!\w)[₹$€£]?\s*-?\d[\d,]*(?:\.\d+)?%?")

SYSTEM_INSTRUCTIONS = """You are FinPilot's AI CFO explanation layer.
The FINPILOT_VERIFIED_RESULT object is calculated by tenant-scoped, deterministic
financial tools and is the only source of financial facts. Never change, invent,
extrapolate, or silently omit its numbers. Do not call payment proceeds accounting
profit unless complete expense data proves that claim. Clearly distinguish observed
facts from forecasts. Give concise, decision-useful guidance, mention material data
limitations, and never claim that an action was executed. This is decision support,
not tax, legal, investment, or accounting advice.

Classify the current question as finance or non_finance. Finance includes business
finance, accounting, payments, cash flow, budgeting, pricing, tax concepts,
fundraising, investment concepts, financial planning, risk, business scenarios,
and questions about interpreting or safely using financial information. Answer any
legitimate finance question. For hypothetical scenarios, state assumptions and use
only numbers from the user's question or FINPILOT_VERIFIED_RESULT. Do not present a
hypothetical as an observed fact. If the question is non_finance, set domain to
non_finance; the application will return its fixed refusal.

Return JSON matching the requested schema. Preserve the meaning of the verified
answer and recommendation. Suggested questions must be answerable from the listed
sources and must not request personal customer data."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "domain": {"type": "string", "enum": ["finance", "non_finance"]},
        "answer": {"type": "string", "minLength": 1, "maxLength": 1800},
        "recommendation": {"type": "string", "minLength": 1, "maxLength": 900},
        "suggestions": {
            "type": "array",
            "minItems": 3,
            "maxItems": 4,
            "items": {"type": "string", "minLength": 2, "maxLength": 140},
        },
    },
    "required": ["domain", "answer", "recommendation", "suggestions"],
    "additionalProperties": False,
}


def _response_text(payload: dict[str, Any]) -> str:
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return str(content["text"])
    raise ValueError("OpenAI response did not contain output text")


def _safe_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
    safe: list[dict[str, str]] = []
    for message in history[-6:]:
        role = message.get("role")
        content = message.get("content", "").strip()
        if role in {"user", "assistant"} and content:
            safe.append({"role": role, "content": _redact_personal_data(content[:1200])})
    return safe


def _redact_personal_data(value: str) -> str:
    value = EMAIL_PATTERN.sub("[redacted-email]", value)
    return PHONE_PATTERN.sub("[redacted-phone]", value)


def _numbers(value: str) -> set[str]:
    return {match.replace(" ", "") for match in NUMBER_PATTERN.findall(value)}


FINANCE_TERMS = {
    "account", "accounting", "asset", "bank", "budget", "burn", "cash", "cfo",
    "cost", "credit", "debt", "expense", "finance", "financial", "forecast", "fund",
    "growth", "hire", "income", "insurance", "interest", "invest", "invoice", "loan",
    "margin", "money", "payment", "payroll", "price", "profit", "razorpay", "refund",
    "reserve", "revenue", "risk", "runway", "sales", "scenario", "settlement", "spend",
    "tax", "transaction", "valuation",
}


def looks_financial(question: str) -> bool:
    words = set(re.findall(r"[a-z]+", question.casefold()))
    return any(word.startswith(term) for word in words for term in FINANCE_TERMS)


def _assert_grounded_numbers(generated: dict[str, Any], verified_facts: dict[str, Any]) -> None:
    allowed = _numbers(json.dumps(verified_facts, ensure_ascii=False, default=str))
    claims = _numbers(f"{generated['answer']} {generated['recommendation']}")
    unsupported = claims - allowed
    if unsupported:
        raise ValueError(f"LLM introduced unsupported numeric claims: {sorted(unsupported)}")


def enhance_cfo_answer(
    *,
    settings: Settings,
    business_id: str,
    question: str,
    verified_result: dict[str, Any],
    history: list[dict[str, str]],
) -> dict[str, Any]:
    """Improve presentation without allowing the model to calculate financial facts."""
    result = dict(verified_result)
    private_context = result.pop("_llm_context", None)
    if not settings.openai_configured and not looks_financial(question):
        result.update({
            "answer": "I can't answer this.",
            "recommendation": "Ask FinPilot a question related to finance or your business finances.",
            "classification": "fact",
            "metrics": [],
            "insights": [],
            "actions": [],
            "tools_used": ["classify_financial_question"],
            "suggestions": verified_result["suggestions"],
        })
        return result
    if not settings.openai_configured:
        return result

    facts = {
        "answer": verified_result["answer"],
        "recommendation": verified_result["recommendation"],
        "classification": verified_result["classification"],
        "metrics": verified_result["metrics"],
        "evidence": verified_result["evidence"],
        "allowed_suggestions": verified_result["suggestions"],
        "financial_context": private_context,
        "hypothetical_numbers_from_question": _numbers(_redact_personal_data(question)),
    }
    messages = _safe_history(history)
    messages.append({
        "role": "user",
        "content": (
            f"CURRENT_QUESTION: {_redact_personal_data(question)}\n"
            f"FINPILOT_VERIFIED_RESULT: {json.dumps(facts, ensure_ascii=False, default=str)}"
        ),
    })
    request = {
        "model": settings.openai_model,
        "instructions": SYSTEM_INSTRUCTIONS,
        "input": messages,
        "store": False,
        "max_output_tokens": settings.openai_max_output_tokens,
        "safety_identifier": hashlib.sha256(business_id.encode()).hexdigest(),
        "prompt_cache_key": "finpilot-ai-cfo-grounded-v1",
        "text": {
            "format": {
                "type": "json_schema",
                "name": "finpilot_cfo_answer",
                "strict": True,
                "schema": OUTPUT_SCHEMA,
            }
        },
    }
    try:
        with httpx.Client(timeout=settings.openai_timeout_seconds) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=request,
            )
            response.raise_for_status()
        generated = json.loads(_response_text(response.json()))
        _assert_grounded_numbers(generated, facts)
        if generated["domain"] == "non_finance":
            result.update({
                "answer": "I can't answer this.",
                "recommendation": "Ask FinPilot a question related to finance or your business finances.",
                "classification": "fact",
                "metrics": [],
                "insights": [],
                "actions": [],
                "tools_used": ["classify_financial_question"],
            })
            return result
        result["answer"] = generated["answer"].strip()
        result["recommendation"] = generated["recommendation"].strip()
        result["suggestions"] = [item.strip() for item in generated["suggestions"] if item.strip()][:4]
        result["engine"] = "openai_responses_with_deterministic_financial_tools"
        result["llm"] = {"provider": "openai", "model": settings.openai_model, "grounded": True, "fallback": False}
        return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        logger.warning("AI CFO language layer unavailable; deterministic fallback used: %s", type(exc).__name__)
        result["llm"] = {"provider": "openai", "model": settings.openai_model, "grounded": True, "fallback": True}
        return result
