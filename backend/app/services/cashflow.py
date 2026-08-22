from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Business, Expense, Refund, Transaction


MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "retail_cashflow_model.json"
MINIMUM_TENANT_HISTORY_DAYS = 14
BUSINESS_TIMEZONE = ZoneInfo("Asia/Kolkata")


@lru_cache
def load_retail_model() -> dict[str, Any]:
    """Retained as an auditable training artifact; client forecasts never read it."""
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def _as_business_day(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BUSINESS_TIMEZONE).date()


def _tenant_daily_history(
    db: Session,
    business_id: str,
    mode: str,
    start: date,
    end: date,
) -> dict[date, dict[str, int]]:
    start_at = datetime.combine(start, datetime.min.time(), tzinfo=BUSINESS_TIMEZONE).astimezone(timezone.utc)
    end_at = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=BUSINESS_TIMEZONE).astimezone(timezone.utc)
    payments = db.scalars(
        select(Transaction).where(
            Transaction.business_id == business_id,
            Transaction.mode == mode,
            Transaction.status == "captured",
            Transaction.provider_created_at >= start_at,
            Transaction.provider_created_at < end_at,
        )
    ).all()
    refunds = db.scalars(
        select(Refund).where(
            Refund.business_id == business_id,
            Refund.mode == mode,
            Refund.status == "processed",
            Refund.provider_created_at >= start_at,
            Refund.provider_created_at < end_at,
        )
    ).all()
    daily: dict[date, dict[str, int]] = defaultdict(lambda: {"inflow": 0, "outflow": 0})
    for payment in payments:
        record = daily[_as_business_day(payment.provider_created_at)]
        record["inflow"] += payment.amount_paise
        record["outflow"] += payment.fee_paise
    for refund in refunds:
        daily[_as_business_day(refund.provider_created_at)]["outflow"] += refund.amount_paise
    return dict(daily)


def build_cashflow(
    db: Session,
    business_id: str,
    mode: str,
    history_days: int = 60,
    forecast_days: int = 30,
    today: date | None = None,
) -> dict[str, Any]:
    as_of = today or datetime.now(BUSINESS_TIMEZONE).date()
    history_start = as_of - timedelta(days=history_days - 1)
    tenant_daily = _tenant_daily_history(db, business_id, mode, history_start, as_of)
    active_tenant_days = sum(1 for value in tenant_daily.values() if value["inflow"] or value["outflow"])
    business = db.get(Business, business_id)
    safe_reserve = int(business.minimum_reserve_paise if business else 0)
    current_cash = int(business.current_cash_paise if business and business.current_cash_paise is not None else 0)
    fixed_daily_opex = round((business.monthly_fixed_expenses_paise or 0) / 30) if business else 0
    expenses = db.scalars(select(Expense).where(Expense.business_id == business_id, Expense.expense_date >= history_start, Expense.expense_date <= as_of)).all()
    expenses_by_day: dict[date, int] = defaultdict(int)
    for expense in expenses:
        expenses_by_day[expense.expense_date] += expense.amount_paise

    daily_nets: dict[date, int] = {}
    for offset in range(history_days):
        day = history_start + timedelta(days=offset)
        record = tenant_daily.get(day, {"inflow": 0, "outflow": 0})
        daily_nets[day] = record["inflow"] - record["outflow"] - expenses_by_day[day]
    opening_balance = current_cash - sum(daily_nets.values())

    points: list[dict[str, Any]] = []
    balance = opening_balance
    for offset in range(history_days):
        day = history_start + timedelta(days=offset)
        record = tenant_daily.get(day, {"inflow": 0, "outflow": 0})
        inflow = record["inflow"]
        outflow = record["outflow"] + expenses_by_day[day]
        balance += inflow - outflow
        points.append(
            {
                "date": day.isoformat(),
                "actual": round(balance / 100, 2),
                "forecast": None,
                "lower": None,
                "upper": None,
                "inflow": round(inflow / 100, 2),
                "outflow": round(outflow / 100, 2),
                "kind": "actual",
            }
        )

    baseline_inflow = round(sum(value["inflow"] for value in tenant_daily.values()) / history_days)
    captured_total = sum(value["inflow"] for value in tenant_daily.values())
    provider_cost_total = sum(value["outflow"] for value in tenant_daily.values())
    provider_cost_ratio = provider_cost_total / captured_total if captured_total else 0.0
    refund_total = sum(refund.amount_paise for refund in db.scalars(select(Refund).where(Refund.business_id == business_id, Refund.mode == mode, Refund.status == "processed")).all())
    return_rate = min(refund_total / captured_total, 1.0) if captured_total else 0.0

    forecast_inflow_total = 0
    forecast_outflow_total = 0
    forecast_balances: list[tuple[date, int]] = []
    for offset in range(1, forecast_days + 1):
        day = as_of + timedelta(days=offset)
        inflow = baseline_inflow
        outflow = round(inflow * provider_cost_ratio + fixed_daily_opex)
        balance += inflow - outflow
        forecast_inflow_total += inflow
        forecast_outflow_total += outflow
        uncertainty = round(inflow * 0.20 * math.sqrt(offset))
        forecast_balances.append((day, balance))
        points.append(
            {
                "date": day.isoformat(),
                "actual": None,
                "forecast": round(balance / 100, 2),
                "lower": round(max(balance - uncertainty, 0) / 100, 2),
                "upper": round((balance + uncertainty) / 100, 2),
                "inflow": round(inflow / 100, 2),
                "outflow": round(outflow / 100, 2),
                "kind": "forecast",
            }
        )

    lowest_day, lowest_balance = min(forecast_balances, key=lambda item: item[1])
    risk_level = "high" if lowest_balance < 0 else "medium" if lowest_balance < safe_reserve else "low"
    cash_available = points[history_days - 1]["actual"]
    return {
        "as_of": as_of.isoformat(),
        "currency": "INR",
        "mode": mode,
        "data_source": "workspace_financials",
        "summary": {
            "cash_available": cash_available,
            "forecast_closing_balance": round(forecast_balances[-1][1] / 100, 2),
            "lowest_balance": round(lowest_balance / 100, 2),
            "lowest_balance_date": lowest_day.isoformat(),
            "safe_reserve": round(safe_reserve / 100, 2),
            "risk_level": risk_level,
        },
        "drivers": {
            "forecast_inflow": round(forecast_inflow_total / 100, 2),
            "forecast_outflow": round(forecast_outflow_total / 100, 2),
            "return_rate": return_rate,
            "variable_cost_ratio": 0.0,
            "payment_fee_ratio": provider_cost_ratio,
            "fixed_daily_opex": round(fixed_daily_opex / 100, 2),
        },
        "model": {
            "name": "tenant_cashflow_baseline_v1",
            "trained_on": "This workspace only",
            "training_period": [history_start.isoformat(), as_of.isoformat()],
            "tenant_history_days": active_tenant_days,
            "minimum_tenant_history_days": MINIMUM_TENANT_HISTORY_DAYS,
            "limitations": ["Forecast confidence is limited until more workspace activity is available.", "Unrecorded bank balances and expenses are not inferred."],
        },
        "points": points,
    }
