"""Deterministic, tenant-scoped financial calculations used by APIs and agents."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Business, DailyFinancialMetric, Expense, FinancialAlert, Refund, Settlement, Transaction
from app.services.cashflow import build_cashflow


def percentage_change(current: float, previous: float) -> float | None:
    return round((current - previous) / abs(previous) * 100, 2) if previous else None


def calculate_net_revenue(gross_paise: int, refunds_paise: int, fees_paise: int, tax_paise: int = 0) -> int:
    return gross_paise - refunds_paise - fees_paise - tax_paise


def calculate_burn_rate(outflow_paise: int, months: float = 1.0) -> int:
    return round(outflow_paise / months) if months > 0 else 0


def calculate_runway(current_cash_paise: int | None, monthly_net_burn_paise: int) -> float | None:
    if current_cash_paise is None or monthly_net_burn_paise <= 0:
        return None
    return round(current_cash_paise / monthly_net_burn_paise, 2)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _records(db: Session, business_id: str, mode: str, start: datetime, end: datetime) -> tuple[list[Transaction], list[Refund], list[Settlement], list[Expense]]:
    transactions = list(db.scalars(select(Transaction).where(
        Transaction.business_id == business_id,
        Transaction.mode == mode,
        Transaction.provider_created_at >= start,
        Transaction.provider_created_at < end,
    )).all())
    refunds = list(db.scalars(select(Refund).where(
        Refund.business_id == business_id,
        Refund.mode == mode,
        Refund.provider_created_at >= start,
        Refund.provider_created_at < end,
    )).all())
    settlements = list(db.scalars(select(Settlement).where(
        Settlement.business_id == business_id,
        Settlement.mode == mode,
        Settlement.provider_created_at >= start,
        Settlement.provider_created_at < end,
    )).all())
    expenses = list(db.scalars(select(Expense).where(
        Expense.business_id == business_id,
        Expense.expense_date >= start.date(),
        Expense.expense_date < end.date(),
    )).all())
    return transactions, refunds, settlements, expenses


def _period(db: Session, business_id: str, mode: str, start: datetime, end: datetime) -> dict[str, Any]:
    transactions, refunds, settlements, expenses = _records(db, business_id, mode, start, end)
    captured = [item for item in transactions if item.status == "captured"]
    failed = [item for item in transactions if item.status == "failed"]
    processed_refunds = [item for item in refunds if item.status == "processed"]
    processed_settlements = [item for item in settlements if item.status == "processed"]
    gross = sum(item.amount_paise for item in captured)
    fees = sum(item.fee_paise for item in captured)
    taxes = sum(item.tax_paise for item in captured)
    refund_amount = sum(item.amount_paise for item in processed_refunds)
    expense_amount = sum(item.amount_paise for item in expenses)
    settled = sum(item.amount_paise for item in processed_settlements)
    net_revenue = calculate_net_revenue(gross, refund_amount, fees, taxes)
    inflow = settled if processed_settlements else net_revenue
    outflow = expense_amount
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "gross_revenue_paise": gross,
        "refunds_paise": refund_amount,
        "fees_paise": fees,
        "tax_paise": taxes,
        "net_revenue_paise": net_revenue,
        "settled_paise": settled,
        "expenses_paise": expense_amount,
        "cash_inflow_paise": inflow,
        "cash_outflow_paise": outflow,
        "net_cashflow_paise": inflow - outflow,
        "attempts": len(transactions),
        "successful": len(captured),
        "failed": len(failed),
        "refund_count": len(processed_refunds),
        "settlement_count": len(processed_settlements),
        "failure_rate": round(len(failed) / len(transactions) * 100, 2) if transactions else 0.0,
        "refund_rate": round(refund_amount / gross * 100, 2) if gross else 0.0,
    }


def financial_summary(db: Session, business_id: str, mode: str, days: int = 30) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    previous_start = start - timedelta(days=days)
    current = _period(db, business_id, mode, start, now)
    previous = _period(db, business_id, mode, previous_start, start)
    business = db.get(Business, business_id)
    cashflow = build_cashflow(db, business_id, mode, history_days=max(days, 30), forecast_days=90)
    current_cash = business.current_cash_paise if business else None
    if current_cash is None and cashflow["summary"]["cash_available"] is not None:
        current_cash = round(cashflow["summary"]["cash_available"] * 100)
    monthly_outflow = current["expenses_paise"]
    if business and business.monthly_fixed_expenses_paise and monthly_outflow == 0:
        monthly_outflow = business.monthly_fixed_expenses_paise
    monthly_net_burn = max(monthly_outflow - current["cash_inflow_paise"], 0)
    runway = calculate_runway(current_cash, monthly_net_burn)
    growth = percentage_change(current["net_revenue_paise"], previous["net_revenue_paise"])
    health = health_score(
        runway_months=runway,
        target_runway=business.target_runway_months if business else 12,
        growth_percent=growth,
        net_cashflow_paise=current["net_cashflow_paise"],
        failure_rate=current["failure_rate"],
        refund_rate=current["refund_rate"],
    )
    return {
        "as_of": now.isoformat(),
        "period_days": days,
        "mode": mode,
        "currency": business.currency if business else "INR",
        "current": current,
        "previous": previous,
        "changes": {
            "net_revenue_percent": growth,
            "net_cashflow_percent": percentage_change(current["net_cashflow_paise"], previous["net_cashflow_paise"]),
            "failure_rate_points": round(current["failure_rate"] - previous["failure_rate"], 2),
            "refund_rate_points": round(current["refund_rate"] - previous["refund_rate"], 2),
        },
        "cash": {
            "current_paise": current_cash,
            "monthly_outflow_paise": monthly_outflow,
            "monthly_net_burn_paise": monthly_net_burn,
            "runway_months": runway,
            "target_runway_months": business.target_runway_months if business else 12,
            "minimum_reserve_paise": business.minimum_reserve_paise if business else 10_000_000,
        },
        "forecast": cashflow,
        "health": health,
        "data_completeness": {
            "payments": bool(current["attempts"] or previous["attempts"]),
            "expenses": bool(current["expenses_paise"] or (business and business.monthly_fixed_expenses_paise)),
            "current_cash": current_cash is not None,
            "settlements": bool(current["settlement_count"] or previous["settlement_count"]),
        },
    }


def health_score(*, runway_months: float | None, target_runway: float, growth_percent: float | None, net_cashflow_paise: int, failure_rate: float, refund_rate: float) -> dict[str, Any]:
    runway_component = 50 if runway_months is None else min(round(runway_months / max(target_runway, 1) * 100), 100)
    growth_component = 50 if growth_percent is None else min(max(round(50 + growth_percent * 2), 0), 100)
    cashflow_component = 85 if net_cashflow_paise > 0 else 50 if net_cashflow_paise == 0 else 20
    payments_component = min(max(round(100 - failure_rate * 5), 0), 100)
    refunds_component = min(max(round(100 - refund_rate * 8), 0), 100)
    score = round(runway_component * .30 + growth_component * .25 + cashflow_component * .20 + payments_component * .15 + refunds_component * .10)
    return {
        "score": score,
        "status": "healthy" if score >= 75 else "watch" if score >= 55 else "at_risk",
        "components": {
            "runway": runway_component,
            "growth": growth_component,
            "cashflow": cashflow_component,
            "payments": payments_component,
            "refunds": refunds_component,
        },
        "limitations": [] if runway_months is not None else ["Runway is unavailable until current cash and expense data are provided."],
    }


def rebuild_daily_metrics(db: Session, business_id: str, mode: str, days: int = 90) -> int:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    transactions, refunds, _settlements, expenses = _records(db, business_id, mode, start, end)
    buckets: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in transactions:
        day = _aware(item.provider_created_at).date()
        buckets[day]["attempts"] += 1
        if item.status == "captured":
            buckets[day]["successful"] += 1
            buckets[day]["gross"] += item.amount_paise
            buckets[day]["fees"] += item.fee_paise + item.tax_paise
        elif item.status == "failed":
            buckets[day]["failed"] += 1
    for item in refunds:
        if item.status == "processed":
            buckets[_aware(item.provider_created_at).date()]["refunds"] += item.amount_paise
    for item in expenses:
        buckets[item.expense_date]["expenses"] += item.amount_paise
    db.execute(delete(DailyFinancialMetric).where(
        DailyFinancialMetric.business_id == business_id,
        DailyFinancialMetric.mode == mode,
        DailyFinancialMetric.metric_date >= start.date(),
    ))
    for metric_date, values in buckets.items():
        gross = values["gross"]
        attempts = values["attempts"]
        net = gross - values["refunds"] - values["fees"] - values["expenses"]
        db.add(DailyFinancialMetric(
            business_id=business_id,
            mode=mode,
            metric_date=metric_date,
            gross_revenue_paise=gross,
            refunds_paise=values["refunds"],
            fees_paise=values["fees"],
            expenses_paise=values["expenses"],
            net_cashflow_paise=net,
            successful_payments=values["successful"],
            failed_payments=values["failed"],
            refund_rate=round(values["refunds"] / gross * 100, 2) if gross else 0,
            failure_rate=round(values["failed"] / attempts * 100, 2) if attempts else 0,
        ))
    db.flush()
    return len(buckets)


def refresh_anomaly_alerts(db: Session, business_id: str, mode: str) -> list[FinancialAlert]:
    metrics = list(db.scalars(select(DailyFinancialMetric).where(
        DailyFinancialMetric.business_id == business_id,
        DailyFinancialMetric.mode == mode,
    ).order_by(DailyFinancialMetric.metric_date.desc()).limit(31)).all())
    if len(metrics) < 3:
        return []
    current, history = metrics[0], metrics[1:]
    rules = [
        ("payment_failure_spike", "Payment failure spike", current.failure_rate, sum(item.failure_rate for item in history) / len(history), 1.8, "%"),
        ("refund_spike", "Refund rate spike", current.refund_rate, sum(item.refund_rate for item in history) / len(history), 1.8, "%"),
    ]
    created: list[FinancialAlert] = []
    for alert_type, title, value, baseline, multiplier, unit in rules:
        if value <= max(baseline * multiplier, baseline + 3):
            continue
        existing = db.scalar(select(FinancialAlert).where(
            FinancialAlert.business_id == business_id,
            FinancialAlert.mode == mode,
            FinancialAlert.alert_type == alert_type,
            FinancialAlert.status.in_(["unread", "read"]),
        ).order_by(FinancialAlert.created_at.desc()).limit(1))
        if existing and existing.created_at.date() == datetime.now(timezone.utc).date():
            continue
        severity = "critical" if value >= max(baseline * 2.5, baseline + 8) else "warning"
        alert = FinancialAlert(
            id=str(uuid4()), business_id=business_id, mode=mode, alert_type=alert_type,
            severity=severity, title=title,
            description=f"{title} moved from a {baseline:.1f}{unit} rolling baseline to {value:.1f}{unit}.",
            metric_value=value, baseline_value=baseline,
            evidence={"metric_date": current.metric_date.isoformat(), "method": "rolling_deviation", "history_days": len(history)},
        )
        db.add(alert)
        created.append(alert)
    db.flush()
    return created
