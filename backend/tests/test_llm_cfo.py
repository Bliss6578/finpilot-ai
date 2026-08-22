import json

import httpx

from app.config import Settings
from app.services.llm_cfo import enhance_cfo_answer


def _verified() -> dict:
    return {
        "answer": "Verified net proceeds are ₹2,434. This is not accounting profit.",
        "recommendation": "Connect complete expenses before making a profit claim.",
        "classification": "recommendation",
        "metrics": [{"label": "Net proceeds", "value": "₹2,434", "detail": "Verified"}],
        "suggestions": ["What is my revenue?", "What is my cash flow?", "What is my success rate?"],
        "evidence": {"tenant_scope": "authenticated_workspace", "sources": ["Razorpay payments"]},
        "engine": "deterministic_financial_tools",
    }


def test_llm_layer_uses_strict_private_grounded_request(monkeypatch) -> None:
    captured = {}

    def fake_post(self, url, **kwargs):
        captured.update({"url": url, **kwargs})
        output = {
            "domain": "finance",
            "answer": "Your verified net proceeds are ₹2,434; this is not accounting profit.",
            "recommendation": "Add complete expenses before making a profit decision.",
            "suggestions": ["What changed?", "What is my cash risk?", "How are payments performing?"],
        }
        return httpx.Response(200, request=httpx.Request("POST", url), json={
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(output)}]}]
        })

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    result = enhance_cfo_answer(
        settings=Settings(openai_api_key="sk-test", openai_model="gpt-test"),
        business_id="tenant-a",
        question="What is my profit?",
        verified_result=_verified(),
        history=[{"role": "user", "content": "Earlier question"}],
    )

    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["json"]["store"] is False
    assert captured["json"]["text"]["format"]["strict"] is True
    assert captured["json"]["safety_identifier"] != "tenant-a"
    assert result["metrics"][0]["value"] == "₹2,434"
    assert result["engine"] == "openai_responses_with_deterministic_financial_tools"
    assert result["llm"]["fallback"] is False


def test_llm_failure_preserves_verified_answer(monkeypatch) -> None:
    def failing_post(self, url, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx.Client, "post", failing_post)
    verified = _verified()
    result = enhance_cfo_answer(
        settings=Settings(openai_api_key="sk-test"),
        business_id="tenant-a",
        question="What is my profit?",
        verified_result=verified,
        history=[],
    )
    assert result["answer"] == verified["answer"]
    assert result["engine"] == "deterministic_financial_tools"
    assert result["llm"]["fallback"] is True


def test_llm_rejects_unsupported_numbers_and_redacts_personal_data(monkeypatch) -> None:
    captured = {}

    def fake_post(self, url, **kwargs):
        captured.update(kwargs)
        output = {
            "domain": "finance",
            "answer": "Your verified net proceeds are ₹9,999.",
            "recommendation": "Call the customer.",
            "suggestions": ["What changed?", "What is my cash risk?", "How are payments performing?"],
        }
        return httpx.Response(200, request=httpx.Request("POST", url), json={
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(output)}]}]
        })

    monkeypatch.setattr(httpx.Client, "post", fake_post)
    verified = _verified()
    result = enhance_cfo_answer(
        settings=Settings(openai_api_key="sk-test"),
        business_id="tenant-a",
        question="Review the payment from buyer@example.com and +91 9093366156",
        verified_result=verified,
        history=[{"role": "user", "content": "buyer@example.com called +91 9093366156"}],
    )
    serialized_input = json.dumps(captured["json"]["input"])
    assert "buyer@example.com" not in serialized_input
    assert "9093366156" not in serialized_input
    assert result["answer"] == verified["answer"]
    assert result["llm"]["fallback"] is True
