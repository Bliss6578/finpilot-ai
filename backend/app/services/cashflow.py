from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Refund, Transaction


MODEL_PATH = Path(__file__).resolve().parents[1] / "data" / "retail_cashflow_model.json"
MINIMUM_TENANT_HISTORY_DAYS = 14
BUSINESS_TIMEZONE = ZoneInfo("Asia/Kolkata")


@lru_cache
def load_retail_model() -> dict[str, Any]:
    return json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def _as_business_day(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BUSINESS_TIMEZONE).date()


def _seasonal_multiplier(model: dict[str, Any], day: date) -> float:
    training = model["training"]
    weekday = float(training["weekday_multipliers"].get(str(day.weekday()), 1))
    month = float(training["month_multipliers"].get(str(day.month), 1))
    return max(weekday * month, 0.05)


def _deterministic_variation(day: date) -> float:
    """Stable demo variation: identical inputs always produce identical charts."""
    return 1 + 0.08 * math.sin(day.toordinal() * 0.83) + 0.04 * math.cos(day.toordinal() * 0.31)


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


def _demo_day(model: dict[str, Any], day: date) -> tuple[int, int]:
    assumptions = model["demo_assumptions"]
    inflow = round(
        int(assumptions["baseline_daily_inflow_paise"])
        * _seasonal_multiplier(model, day)
        * _deterministic_variation(day)
    )
    outflow = round(
        inflow
        * (
            float(assumptions["variable_cost_ratio"])
            + float(assumptions["payment_fee_ratio"])
            + float(model["training"]["return_rate"])
        )
        + int(assumptions["fixed_daily_opex_paise"])
    )
    return max(inflow, 0), max(outflow, 0)


def build_cashflow(
    db: Session,
    business_id: str,
    mode: str,
    history_days: int = 60,
    forecast_days: int = 30,
    today: date | None = None,
) -> dict[str, Any]:
    model = load_retail_model()
    as_of = today or datetime.now(BUSINESS_TIMEZONE).date()
    history_start = as_of - timedelta(days=history_days - 1)
    tenant_daily = _tenant_daily_history(db, business_id, mode, history_start, as_of)
    active_tenant_days = sum(1 for value in tenant_daily.values() if value["inflow"] or value["outflow"])
    use_tenant_history = active_tenant_days >= MINIMUM_TENANT_HISTORY_DAYS
    has_tenant_history = active_tenant_days > 0
    source = (
        "razorpay_history"
        if use_tenant_history
        else "razorpay_plus_dataset"
        if has_tenant_history
        else "uci_online_retail_ii_demo"
    )
    assumptions = model["demo_assumptions"]
    safe_reserve = int(assumptions["safe_reserve_paise"])
    opening_balance = int(assumptions["opening_balance_paise"])

    points: list[dict[str, Any]] = []
    balance = opening_balance
    observed_inflows: list[int] = []
    for offset in range(history_days):
        day = history_start + timedelta(days=offset)
        record = tenant_daily.get(day)
        if record is not None:
            inflow = record["inflow"]
            outflow = round(
                record["outflow"]
                + inflow * float(assumptions["variable_cost_ratio"])
                + int(assumptions["fixed_daily_opex_paise"])
            )
        elif use_tenant_history:
            # A day without a payment still carries the modeled fixed operating cost.
            inflow = 0
            outflow = int(assumptions["fixed_daily_opex_paise"])
        else:
            inflow, outflow = _demo_day(model, day)
        balance += inflow - outflow
        if inflow:
            observed_inflows.append(inflow)
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

    if has_tenant_history and observed_inflows:
        observed_baseline = int(statistics.median(observed_inflows))
        dataset_baseline = int(assumptions["baseline_daily_inflow_paise"])
        personalization_weight = min(active_tenant_days / MINIMUM_TENANT_HISTORY_DAYS, 1)
        baseline_inflow = round(
            dataset_baseline * (1 - personalization_weight)
            + observed_baseline * personalization_weight
        )
    else:
        baseline_inflow = int(assumptions["baseline_daily_inflow_paise"])

    forecast_inflow_total = 0
    forecast_outflow_total = 0
    forecast_balances: list[tuple[date, int]] = []
    for offset in range(1, forecast_days + 1):
        day = as_of + timedelta(days=offset)
        inflow = round(baseline_inflow * _seasonal_multiplier(model, day))
        if has_tenant_history:
            outflow = round(
                inflow
                * (
                    float(assumptions["payment_fee_ratio"])
                    + float(model["training"]["return_rate"])
                    + float(assumptions["variable_cost_ratio"])
                )
                + int(assumptions["fixed_daily_opex_paise"])
            )
        else:
            inflow, outflow = _demo_day(model, day)
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
        "data_source": source,
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
            "return_rate": float(model["training"]["return_rate"]),
            "variable_cost_ratio": float(assumptions["variable_cost_ratio"]),
            "payment_fee_ratio": float(assumptions["payment_fee_ratio"]),
            "fixed_daily_opex": round(int(assumptions["fixed_daily_opex_paise"]) / 100, 2),
        },
        "model": {
            "name": model["model_name"],
            "trained_on": model["source"]["dataset"],
            "training_period": [model["source"]["first_date"], model["source"]["last_date"]],
            "tenant_history_days": active_tenant_days,
            "minimum_tenant_history_days": MINIMUM_TENANT_HISTORY_DAYS,
            "limitations": model["limitations"],
        },
        "points": points,
    }
