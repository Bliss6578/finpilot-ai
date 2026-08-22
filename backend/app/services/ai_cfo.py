from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Refund, Settlement, Transaction
from app.services.cashflow import build_cashflow
from app.services.financial_engine import financial_summary


PERIOD_DAYS = 30


@dataclass
class PeriodMetrics:
    attempts: int = 0
    captured: int = 0
    failed: int = 0
    gross_paise: int = 0
    fees_paise: int = 0
    refunds_paise: int = 0
    refund_count: int = 0
    settled_paise: int = 0
    settlement_count: int = 0

    @property
    def net_proceeds_paise(self) -> int:
        return self.gross_paise - self.fees_paise - self.refunds_paise

    @property
    def success_rate(self) -> float:
        return round(self.captured / self.attempts * 100, 1) if self.attempts else 0.0

    @property
    def average_order_paise(self) -> int:
        return round(self.gross_paise / self.captured) if self.captured else 0


def _inr(paise: int) -> str:
    return f"₹{paise / 100:,.0f}"


def _change(current: int | float, previous: int | float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100, 1)


def _change_text(value: float | None) -> str:
    if value is None:
        return "No comparable prior-period baseline"
    direction = "up" if value > 0 else "down" if value < 0 else "unchanged"
    return f"{abs(value):.1f}% {direction} vs previous 30 days"


def _period_metrics(
    transactions: list[Transaction],
    refunds: list[Refund],
    settlements: list[Settlement],
    start: datetime,
    end: datetime,
) -> PeriodMetrics:
    tx = [item for item in transactions if start <= _aware(item.provider_created_at) < end]
    period_refunds = [item for item in refunds if start <= _aware(item.provider_created_at) < end]
    period_settlements = [item for item in settlements if start <= _aware(item.provider_created_at) < end]
    captured = [item for item in tx if item.status == "captured"]
    processed_refunds = [item for item in period_refunds if item.status == "processed"]
    processed_settlements = [item for item in period_settlements if item.status == "processed"]
    return PeriodMetrics(
        attempts=len(tx),
        captured=len(captured),
        failed=sum(item.status == "failed" for item in tx),
        gross_paise=sum(item.amount_paise for item in captured),
        fees_paise=sum(item.fee_paise for item in captured),
        refunds_paise=sum(item.amount_paise for item in processed_refunds),
        refund_count=len(processed_refunds),
        settled_paise=sum(item.amount_paise for item in processed_settlements),
        settlement_count=len(processed_settlements),
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _metric(label: str, value: str, detail: str) -> dict[str, str]:
    return {"label": label, "value": value, "detail": detail}


def _suggestions(current: PeriodMetrics) -> list[str]:
    suggestions = [
        "What is my net payment revenue this month?",
        "How healthy is my payment success rate?",
        "What does my 30-day cash-flow forecast show?",
    ]
    if current.refund_count:
        suggestions.insert(0, "Why are my refunds changing?")
    if current.settlement_count:
        suggestions.append("How much has Razorpay settled to my bank?")
    return suggestions[:4]


def build_cfo_context(db: Session, business_id: str, mode: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=PERIOD_DAYS)
    previous_start = current_start - timedelta(days=PERIOD_DAYS)
    transactions = list(
        db.scalars(
            select(Transaction).where(
                Transaction.business_id == business_id,
                Transaction.mode == mode,
                Transaction.provider_created_at >= previous_start,
            )
        ).all()
    )
    refunds = list(
        db.scalars(
            select(Refund).where(
                Refund.business_id == business_id,
                Refund.mode == mode,
                Refund.provider_created_at >= previous_start,
            )
        ).all()
    )
    settlements = list(
        db.scalars(
            select(Settlement).where(
                Settlement.business_id == business_id,
                Settlement.mode == mode,
                Settlement.provider_created_at >= previous_start,
            )
        ).all()
    )
    current = _period_metrics(transactions, refunds, settlements, current_start, now)
    previous = _period_metrics(transactions, refunds, settlements, previous_start, current_start)
    dated_items = [
        _aware(item.provider_created_at)
        for item in [*transactions, *refunds, *settlements]
        if item.provider_created_at
    ]
    cashflow = build_cashflow(db, business_id, mode, history_days=90, forecast_days=30)
    return {
        "as_of": now.isoformat(),
        "mode": mode,
        "current": current,
        "previous": previous,
        "cashflow": cashflow,
        "latest_data_at": max(dated_items).isoformat() if dated_items else None,
        "suggestions": _suggestions(current),
    }


def answer_cfo_question(db: Session, business_id: str, mode: str, question: str) -> dict[str, Any]:
    context = build_cfo_context(db, business_id, mode)
    current: PeriodMetrics = context["current"]
    previous: PeriodMetrics = context["previous"]
    cashflow = context["cashflow"]
    normalized = question.casefold()
    intelligence = financial_summary(db, business_id, mode, PERIOD_DAYS)
    has_data = current.attempts + previous.attempts + current.refund_count + previous.refund_count > 0

    if not has_data:
        answer = "This workspace has no synchronized Razorpay activity in the last 60 days, so I cannot make a client-specific financial claim yet."
        recommendation = "Run Razorpay Sync or receive a test webhook, then ask again. Paymentor will keep this workspace isolated from every other client's data."
        metrics = [
            _metric("Payment attempts", "0", "Last 30 days"),
            _metric("Refunds", "0", "Last 30 days"),
            _metric("Data status", "Waiting", "No current Razorpay evidence"),
        ]
    elif any(term in normalized for term in ("refund", "return")):
        change = _change(current.refunds_paise, previous.refunds_paise)
        refund_rate = current.refunds_paise / current.gross_paise * 100 if current.gross_paise else 0
        answer = (
            f"Processed refunds total {_inr(current.refunds_paise)} across {current.refund_count} refunds in the last 30 days. "
            f"That is {refund_rate:.1f}% of captured payment value. {_change_text(change)}."
        )
        recommendation = (
            "Review the linked payment and refund reason for the largest refunds. Paymentor cannot attribute refunds to products or campaigns until order-level commerce data is connected."
            if current.refund_count
            else "No processed refund requires action in this period. Continue monitoring webhook and synchronization health."
        )
        metrics = [
            _metric("Refunded", _inr(current.refunds_paise), f"{current.refund_count} processed"),
            _metric("Refund rate", f"{refund_rate:.1f}%", "Of captured value"),
            _metric("Previous period", _inr(previous.refunds_paise), f"{previous.refund_count} processed"),
        ]
    elif any(term in normalized for term in ("profit", "revenue", "sales", "income", "earn")):
        change = _change(current.net_proceeds_paise, previous.net_proceeds_paise)
        answer = (
            f"Net Razorpay payment proceeds are {_inr(current.net_proceeds_paise)} for the last 30 days: "
            f"{_inr(current.gross_paise)} captured, less {_inr(current.refunds_paise)} refunds and {_inr(current.fees_paise)} Razorpay fees. "
            f"{_change_text(change)}. This is not accounting profit because payroll, inventory, tax, advertising, and other expenses are not connected."
        )
        recommendation = "Use net payment proceeds for collection monitoring. Connect expense and bank data before using Paymentor for profit or runway decisions."
        metrics = [
            _metric("Gross captured", _inr(current.gross_paise), f"{current.captured} payments"),
            _metric("Net proceeds", _inr(current.net_proceeds_paise), "After refunds and Razorpay fees"),
            _metric("Average order", _inr(current.average_order_paise), "Captured payments only"),
        ]
    elif any(term in normalized for term in ("success", "fail", "capture", "payment")):
        change = _change(current.success_rate, previous.success_rate)
        answer = (
            f"The payment success rate is {current.success_rate:.1f}%: {current.captured} captured and {current.failed} failed out of {current.attempts} attempts in the last 30 days. "
            f"{_change_text(change)}."
        )
        recommendation = "Inspect recent failed payments by method before changing checkout settings. A reliable diagnosis needs enough attempts and Razorpay failure-reason data."
        metrics = [
            _metric("Success rate", f"{current.success_rate:.1f}%", "Last 30 days"),
            _metric("Captured", str(current.captured), f"{_inr(current.gross_paise)} collected"),
            _metric("Failed", str(current.failed), f"{current.attempts} total attempts"),
        ]
    elif any(term in normalized for term in ("settle", "bank", "payout")):
        change = _change(current.settled_paise, previous.settled_paise)
        answer = (
            f"Razorpay settlements marked processed total {_inr(current.settled_paise)} across {current.settlement_count} settlements in the last 30 days. "
            f"{_change_text(change)}."
        )
        recommendation = "Reconcile processed settlements with your bank statement before treating them as confirmed bank cash."
        metrics = [
            _metric("Settled", _inr(current.settled_paise), f"{current.settlement_count} processed"),
            _metric("Captured", _inr(current.gross_paise), "Payment evidence"),
            _metric("Previous period", _inr(previous.settled_paise), f"{previous.settlement_count} processed"),
        ]
    elif any(term in normalized for term in ("health", "score", "condition")):
        health = intelligence["health"]
        answer = (
            f"The deterministic financial health score is {health['score']} out of 100 ({health['status'].replace('_', ' ')}). "
            f"Its components are runway {health['components']['runway']}, growth {health['components']['growth']}, cash flow {health['components']['cashflow']}, payments {health['components']['payments']}, and refunds {health['components']['refunds']}."
        )
        recommendation = health["limitations"][0] if health["limitations"] else "Review the lowest-scoring component first; the score is calculated by Paymentor, not estimated by the language layer."
        metrics = [
            _metric("Health score", f"{health['score']} / 100", health["status"].replace("_", " ").title()),
            _metric("Payment health", str(health["components"]["payments"]), "Deterministic component"),
            _metric("Cash-flow health", str(health["components"]["cashflow"]), "Deterministic component"),
        ]
    elif any(term in normalized for term in ("cash", "forecast", "runway", "reserve", "risk", "burn", "hire", "marketing", "afford", "spend")):
        summary = cashflow["summary"]
        source = cashflow["data_source"]
        runway = intelligence["cash"]["runway_months"]
        burn = intelligence["cash"]["monthly_net_burn_paise"]
        answer = f"The 30-day modeled closing cash position is ₹{summary['forecast_closing_balance']:,.0f}, with a projected low of ₹{summary['lowest_balance']:,.0f} on {summary['lowest_balance_date']}. Risk is {summary['risk_level']}."
        if runway is None:
            answer += " Verified runway is unavailable because current cash and complete expense data are not both available."
        else:
            answer += f" Deterministic monthly net burn is {_inr(burn)} and runway is {runway:.1f} months."
        recommendation = "Add current cash and expenses in Settings before making a high-value commitment." if runway is None else "Run the decision in Scenario Lab before committing cash; forecasts are planning estimates, not guarantees."
        metrics = [
            _metric("Modeled close", f"₹{summary['forecast_closing_balance']:,.0f}", "Next 30 days"),
            _metric("Projected low", f"₹{summary['lowest_balance']:,.0f}", summary["lowest_balance_date"]),
            _metric("Safe reserve", f"₹{summary['safe_reserve']:,.0f}", f"{summary['risk_level'].title()} risk"),
        ]
    else:
        answer = (
            f"In the last 30 days this workspace recorded {current.attempts} payment attempts, {_inr(current.gross_paise)} captured value, "
            f"{_inr(current.refunds_paise)} processed refunds, and {_inr(current.net_proceeds_paise)} net payment proceeds."
        )
        recommendation = "Ask about revenue, refunds, payment success, settlements, or the cash-flow forecast for a deeper evidence-backed answer."
        metrics = [
            _metric("Net proceeds", _inr(current.net_proceeds_paise), "After refunds and Razorpay fees"),
            _metric("Success rate", f"{current.success_rate:.1f}%", f"{current.attempts} attempts"),
            _metric("Settled", _inr(current.settled_paise), f"{current.settlement_count} processed"),
        ]

    tool_names = ["get_financial_summary"]
    if any(term in normalized for term in ("refund", "return")):
        tool_names += ["get_refunds", "compare_periods"]
    elif any(term in normalized for term in ("cash", "forecast", "runway", "reserve", "risk", "burn", "hire", "marketing", "afford", "spend")):
        tool_names += ["get_cashflow", "calculate_burn_and_runway", "forecast_cashflow"]
    elif any(term in normalized for term in ("health", "score", "condition")):
        tool_names += ["get_financial_health_score"]
    elif any(term in normalized for term in ("settle", "bank", "payout")):
        tool_names += ["get_settlements"]
    elif any(term in normalized for term in ("success", "fail", "capture", "payment")):
        tool_names += ["get_transactions", "compare_periods"]
    else:
        tool_names += ["get_revenue", "compare_periods"]
    return {
        "answer": answer,
        "recommendation": recommendation,
        "classification": "recommendation",
        "metrics": metrics,
        "insights": [
            {"type": "positive" if current.net_proceeds_paise >= 0 else "warning", "title": "Net payment proceeds", "value": _inr(current.net_proceeds_paise)},
            {"type": "warning" if current.failed else "positive", "title": "Payment success", "value": f"{current.success_rate:.1f}%"},
        ],
        "actions": [
            {"label": "Run a scenario", "action": "open_scenario_lab"},
            {"label": "View cash-flow forecast", "action": "open_cashflow"},
        ],
        "tools_used": tool_names,
        "engine": "deterministic_financial_tools",
        "suggestions": context["suggestions"],
        "evidence": {
            "tenant_scope": "authenticated_workspace",
            "mode": mode,
            "period_days": PERIOD_DAYS,
            "latest_data_at": context["latest_data_at"],
            "cashflow_source": cashflow["data_source"],
            "sources": ["Razorpay payments", "Razorpay refunds", "Razorpay settlements", "Paymentor cash-flow model"],
        },
        "_llm_context": {
            "currency": intelligence["currency"],
            "current_period": intelligence["current"],
            "previous_period": intelligence["previous"],
            "period_changes": intelligence["changes"],
            "cash": intelligence["cash"],
            "financial_health": intelligence["health"],
            "data_completeness": intelligence["data_completeness"],
            "forecast_summary": cashflow["summary"],
        },
    }
