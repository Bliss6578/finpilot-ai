"""FinPilot's native, evidence-first finance agent.

The agent is deliberately small and auditable: it plans a question, executes
tenant-scoped financial tools, and composes an answer from verified outputs.
No third-party language model is required and no customer record leaves the
FinPilot backend.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Any

from sqlalchemy.orm import Session

from app.services.ai_cfo import answer_cfo_question
from app.services.financial_engine import financial_summary
from app.services.finqa_router import route_reasoning
from app.services.scenarios import simulate


FINANCE_VOCABULARY = {
    "accounting", "asset", "bank", "budget", "burn", "cash", "cfo",
    "cost", "credit", "debt", "expense", "finance", "financial",
    "forecast", "fund", "growth", "hire", "income", "insurance",
    "interest", "invest", "invoice", "loan", "margin", "money",
    "payment", "payroll", "price", "profit", "razorpay", "refund",
    "reserve", "revenue", "risk", "runway", "sales", "scenario",
    "settlement", "spend", "tax", "transaction", "valuation",
    "working capital", "break even", "break-even", "roi", "aov",
}

FINANCE_EXPLANATIONS = {
    "working capital": "Working capital is current assets minus current liabilities. Positive working capital generally means the business can cover near-term obligations, but unusually high working capital can also signal slow inventory or collections.",
    "break even": "Break-even is the point where revenue equals fixed and variable costs. Break-even revenue equals fixed costs divided by contribution-margin percentage.",
    "break-even": "Break-even is the point where revenue equals fixed and variable costs. Break-even revenue equals fixed costs divided by contribution-margin percentage.",
    "gross margin": "Gross margin is revenue minus direct cost of goods or services, divided by revenue. It measures unit economics before operating expenses.",
    "cash flow": "Cash flow tracks money entering and leaving the business. Positive profit does not guarantee positive cash flow because collection and payment timing differ.",
    "runway": "Cash runway estimates how long available cash can support the current net burn rate. It is current cash divided by monthly net burn.",
    "roi": "Return on investment compares net benefit with the cost of an investment. Use consistent time periods and include all material costs before comparing options.",
}

INTENT_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("refund_analysis", ("refund", "return", "chargeback"), ("get_refunds", "compare_periods")),
    ("settlement_analysis", ("settle", "bank payout", "utr"), ("get_settlements", "reconcile_settlements")),
    ("payment_health", ("payment", "success", "failure", "failed", "capture"), ("get_transactions", "compare_periods")),
    ("financial_health", ("health", "score", "condition"), ("get_financial_health_score",)),
    ("cashflow_forecast", ("cash", "forecast", "runway", "reserve", "burn", "liquidity"), ("get_cashflow", "forecast_cashflow")),
    ("revenue_analysis", ("revenue", "sales", "income", "profit", "margin", "earn"), ("get_revenue", "compare_periods")),
)


@dataclass(frozen=True)
class AgentPlan:
    domain: str
    intent: str
    period_days: int
    tools: tuple[str, ...]
    scenario_type: str | None = None
    scenario_parameters: dict[str, float] | None = None


def _words(value: str) -> set[str]:
    return set(re.findall(r"[a-z]+", value.casefold()))


def is_financial_question(question: str) -> bool:
    normalized = question.casefold()
    words = _words(question)
    return any(term in normalized for term in FINANCE_VOCABULARY) or bool(
        words & {"afford", "pricing", "salary", "capital", "equity", "dividend", "ebitda"}
    )


def _period_days(question: str) -> int:
    normalized = question.casefold()
    match = re.search(r"(?:last|past|next|for)\s+(\d{1,3})\s+days?", normalized)
    if match:
        return min(max(int(match.group(1)), 1), 365)
    if "week" in normalized:
        return 7
    if "quarter" in normalized:
        return 90
    if "year" in normalized or "annual" in normalized:
        return 365
    return 30


MONEY_PATTERN = re.compile(r"(?:₹|rs\.?|inr)\s*(\d[\d,]*(?:\.\d+)?)\s*(lakh|lac|crore|k)?|(?<!\w)(\d[\d,]*(?:\.\d+)?)\s*(lakh|lac|crore|k)(?!\w)")


def _money_matches(question: str) -> list[tuple[int, int, int]]:
    matches = list(MONEY_PATTERN.finditer(question.casefold()))
    if not matches:
        plain = list(re.finditer(r"(?<!\w)(\d[\d,]{2,}(?:\.\d+)?)(?!\w)", question.casefold()))
        matches = plain[-1:] if plain else []
    values = []
    for match in matches:
        amount = match.group(1) or (match.group(3) if match.lastindex and match.lastindex >= 3 else None)
        suffix = match.group(2) or (match.group(4) if match.lastindex and match.lastindex >= 4 else None)
        value = float((amount or "0").replace(",", ""))
        multiplier = {"k": 1_000, "lakh": 100_000, "lac": 100_000, "crore": 10_000_000}.get(suffix or "", 1)
        values.append((match.start(), match.end(), round(value * multiplier * 100)))
    return values


def _money_near(question: str, keywords: tuple[str, ...]) -> int | None:
    normalized = question.casefold()
    values = _money_matches(question)
    positions = [normalized.find(keyword) for keyword in keywords if keyword in normalized]
    if not values or not positions:
        return None
    return min(values, key=lambda item: min(abs(item[0] - position) for position in positions))[2]


def _percent(question: str) -> float | None:
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*%", question)
    return float(match.group(1)) if match else None


def _percent_near(question: str, keywords: tuple[str, ...]) -> float | None:
    normalized = question.casefold()
    matches = list(re.finditer(r"(-?\d+(?:\.\d+)?)\s*%", normalized))
    positions = [normalized.find(keyword) for keyword in keywords if keyword in normalized]
    if not matches or not positions:
        return None
    following = [match for match in matches if any(0 <= match.start() - position <= 45 for position in positions)]
    if following:
        match = min(following, key=lambda item: min(item.start() - position for position in positions if item.start() >= position))
        return float(match.group(1))
    match = min(matches, key=lambda item: min(abs(item.start() - position) for position in positions))
    return float(match.group(1))


def _scenario(question: str) -> tuple[str | None, dict[str, float] | None]:
    normalized = question.casefold()
    percent = _percent(question)
    components: list[str] = []
    parameters: dict[str, float] = {}
    hire_money = _money_near(question, ("salary", "hire", "employee", "developer", "person", "people"))
    if any(term in normalized for term in ("hire", "salary", "employee", "developer")) and hire_money is not None:
        count_match = re.search(r"(?:hire|add|employ)\s+(\d+)", normalized)
        employees = float(count_match.group(1)) if count_match else 1.0
        salary = hire_money / 12 if any(term in normalized for term in ("per year", "annual salary", "annually", "per annum")) else hire_money
        parameters.update(employees=employees, monthly_salary_paise=float(salary))
        parameters["monthly_cost_paise"] = employees * salary
        components.append("hire")
    marketing_money = _money_near(question, ("marketing", "advertising", "campaign", "ads"))
    if any(term in normalized for term in ("marketing", "advertising", "campaign", "ad spend", "ads")) and marketing_money is not None:
        parameters["monthly_budget_paise"] = float(marketing_money)
        parameters["monthly_cost_paise"] = parameters.get("monthly_cost_paise", 0) + marketing_money
        components.append("marketing")
    if any(term in normalized for term in ("revenue", "sales")) and percent is not None:
        revenue_percent = _percent_near(question, ("revenue", "sales")) or percent
        signed = -abs(revenue_percent) if any(term in normalized for term in ("drop", "decrease", "fall", "down")) else revenue_percent
        parameters["revenue_change_percent"] = signed
        components.append("revenue")
    if any(term in normalized for term in ("reduce expense", "reduce cost", "cut cost", "cut expense", "expense reduction", "cost reduction")) and percent is not None:
        expense_percent = _percent_near(question, ("expense", "expenses", "cost", "costs")) or percent
        parameters["expense_change_percent"] = -abs(expense_percent)
        components.append("expense_reduction")
    purchase_money = _money_near(question, ("purchase", "buy", "equipment", "machine", "one-time", "one time", "capex"))
    if any(term in normalized for term in ("purchase", "buy", "equipment", "machine", "one-time", "one time", "capex")) and purchase_money is not None:
        parameters["one_time_paise"] = float(purchase_money)
        components.append("one_time_purchase")
    unique = list(dict.fromkeys(components))
    if len(unique) > 1:
        return "custom", parameters
    if unique == ["hire"]:
        return "new_hire", {key: parameters[key] for key in ("employees", "monthly_salary_paise")}
    if unique == ["marketing"]:
        return "marketing", {"monthly_budget_paise": parameters["monthly_budget_paise"]}
    if unique == ["revenue"]:
        return "revenue_change", {"revenue_change_percent": parameters["revenue_change_percent"]}
    if unique == ["expense_reduction"]:
        return "expense_reduction", {"expense_change_percent": abs(parameters["expense_change_percent"])}
    if unique == ["one_time_purchase"]:
        return "one_time_purchase", {"one_time_paise": parameters["one_time_paise"]}
    return None, None


def plan_financial_question(question: str) -> AgentPlan:
    normalized = question.casefold()
    if any(term in normalized for term in ("another client", "other client's", "other clients", "database password", "reveal every client", "reveal secret", "api secret")):
        return AgentPlan("non_finance", "reject", _period_days(question), ("enforce_tenant_privacy",))
    if not is_financial_question(question):
        return AgentPlan("non_finance", "reject", _period_days(question), ("classify_financial_question",))
    scenario_type, parameters = _scenario(question)
    if scenario_type:
        return AgentPlan("finance", "decision_scenario", _period_days(question), ("get_financial_summary", "simulate_scenario", "evaluate_reserve_risk"), scenario_type, parameters)
    for intent, terms, tools in INTENT_RULES:
        if any(term in normalized for term in terms):
            return AgentPlan("finance", intent, _period_days(question), ("get_financial_summary", *tools))
    return AgentPlan("finance", "finance_explanation", _period_days(question), ("get_financial_summary", "explain_financial_concept"))


def _scenario_answer(summary: dict[str, Any], plan: AgentPlan) -> dict[str, Any]:
    try:
        result = simulate(summary, plan.scenario_type or "custom", plan.scenario_parameters or {})
    except ValueError as exc:
        return {
            "answer": str(exc),
            "recommendation": "Save current cash and monthly expenses in Settings, then rerun this question for a client-specific result.",
            "classification": "forecast",
            "metrics": [],
            "actions": [{"label": "Add cash policy", "action": "open_settings"}],
        }
    scenario = result["scenario"]
    difference = result["difference"]
    runway = "cash-generative" if scenario["runway_months"] is None else f"{scenario['runway_months']:.1f} months"
    return {
        "answer": (
            f"Under this scenario, projected cash after 90 days is ₹{scenario['cash_90d_paise'] / 100:,.0f} "
            f"and estimated runway is {runway}. The 90-day cash difference from baseline is "
            f"₹{difference['cash_90d_paise'] / 100:,.0f}."
        ),
        "recommendation": "Treat this as a planning estimate. Review the assumptions in Scenario Lab before approving the decision.",
        "classification": "forecast",
        "metrics": [
            {"label": "90-day cash", "value": f"₹{scenario['cash_90d_paise'] / 100:,.0f}", "detail": "Scenario result"},
            {"label": "Monthly outflow", "value": f"₹{scenario['monthly_outflow_paise'] / 100:,.0f}", "detail": "After scenario"},
            {"label": "Runway", "value": runway, "detail": "Deterministic estimate"},
        ],
        "actions": [{"label": "Open Scenario Lab", "action": "open_scenario_lab"}],
        "scenario_result": result,
        "suggestions": [
            "What if revenue decreases by 10%?",
            "Can I hire 2 people at ₹50,000 per month?",
            "What happens if I cut expenses by 8%?",
            "Can I afford a one-time purchase of ₹2 lakh?",
        ],
    }


def run_finpilot_agent(db: Session, business_id: str, mode: str, question: str) -> dict[str, Any]:
    """Plan and answer a finance question using only this tenant's verified tools."""
    plan = plan_financial_question(question)
    if plan.domain == "non_finance":
        return {
            "answer": "I can't answer this.",
            "recommendation": "Ask FinPilot a question related to finance or your business finances.",
            "classification": "fact", "metrics": [], "insights": [], "actions": [],
            "tools_used": list(plan.tools), "engine": "finpilot_native_finance_agent",
            "suggestions": ["What is my net revenue?", "How much runway do I have?", "What is affecting payment success?"],
            "evidence": {"tenant_scope": "authenticated_workspace", "mode": mode, "period_days": plan.period_days, "latest_data_at": None, "cashflow_source": "workspace_financial_records", "sources": []},
            "agent": {"plan": asdict(plan), "confidence": 1.0, "privacy": "processed_inside_finpilot"},
        }

    reasoning_reference = route_reasoning(question)
    verified = answer_cfo_question(db, business_id, mode, question)
    summary = financial_summary(db, business_id, mode, plan.period_days)
    if plan.intent == "decision_scenario":
        verified.update(_scenario_answer(summary, plan))
    elif plan.intent == "finance_explanation":
        normalized = question.casefold()
        concept = next((value for term, value in FINANCE_EXPLANATIONS.items() if term in normalized), None)
        if concept:
            verified["answer"] = concept
            verified["recommendation"] = "Use the formula with complete, consistently dated business records before making a decision. FinPilot can personalize it as more financial sources are connected."
            verified["classification"] = "fact"
            verified["metrics"] = []
    learned_tools = ("finqa_symbolic_reasoning_router",) if reasoning_reference else ()
    verified["tools_used"] = list(dict.fromkeys((*plan.tools, *learned_tools, *verified.get("tools_used", []))))
    verified["engine"] = "finpilot_native_finance_agent"
    completeness = summary["data_completeness"]
    available = sum(bool(value) for value in completeness.values())
    confidence = round(0.45 + available / max(len(completeness), 1) * 0.5, 2)
    trace_source = f"{business_id}:{mode}:{question}:{verified['evidence'].get('latest_data_at')}"
    verified["agent"] = {
        "plan": asdict(plan),
        "confidence": confidence,
        "data_completeness": completeness,
        "evidence_id": hashlib.sha256(trace_source.encode()).hexdigest()[:16],
        "privacy": "processed_inside_finpilot",
        "reasoning_reference": reasoning_reference,
    }
    verified.pop("_llm_context", None)
    return verified
