"""Deterministic what-if modelling; no LLM arithmetic is permitted here."""

from __future__ import annotations

from typing import Any


def simulate(summary: dict[str, Any], scenario_type: str, parameters: dict[str, float]) -> dict[str, Any]:
    cash = summary["cash"]
    current = summary["current"]
    baseline_cash = cash["current_paise"]
    if baseline_cash is None:
        raise ValueError("Add the current cash balance in Settings before running a decision scenario")
    baseline_inflow = current["cash_inflow_paise"]
    baseline_outflow = cash["monthly_outflow_paise"]
    monthly_inflow = baseline_inflow
    monthly_outflow = baseline_outflow
    one_time = round(parameters.get("one_time_paise", 0))

    if scenario_type == "new_hire":
        employees = max(round(parameters.get("employees", 1)), 0)
        salary = max(round(parameters.get("monthly_salary_paise", 0)), 0)
        monthly_outflow += employees * salary
    elif scenario_type == "marketing":
        monthly_outflow += max(round(parameters.get("monthly_budget_paise", 0)), 0)
    elif scenario_type == "revenue_change":
        monthly_inflow = round(monthly_inflow * (1 + parameters.get("revenue_change_percent", 0) / 100))
    elif scenario_type == "expense_reduction":
        reduction = min(max(parameters.get("expense_change_percent", 0), 0), 100)
        monthly_outflow = round(monthly_outflow * (1 - reduction / 100))
    elif scenario_type == "one_time_purchase":
        pass
    elif scenario_type == "custom":
        monthly_inflow = round(monthly_inflow * (1 + parameters.get("revenue_change_percent", 0) / 100))
        monthly_outflow = round(monthly_outflow * (1 + parameters.get("expense_change_percent", 0) / 100))
        monthly_outflow += max(round(parameters.get("monthly_cost_paise", 0)), 0)
    else:
        raise ValueError("Unsupported scenario type")

    def outcome(inflow: int, outflow: int, initial_cash: int) -> dict[str, Any]:
        net_burn = max(outflow - inflow, 0)
        runway = round(initial_cash / net_burn, 2) if net_burn else None
        cash_90d = initial_cash + (inflow - outflow) * 3
        return {
            "monthly_inflow_paise": inflow,
            "monthly_outflow_paise": outflow,
            "monthly_net_burn_paise": net_burn,
            "runway_months": runway,
            "cash_90d_paise": cash_90d,
            "break_even_revenue_paise": outflow,
        }

    baseline = outcome(baseline_inflow, baseline_outflow, baseline_cash)
    scenario = outcome(monthly_inflow, monthly_outflow, baseline_cash - one_time)
    runway_difference = None
    if baseline["runway_months"] is not None and scenario["runway_months"] is not None:
        runway_difference = round(scenario["runway_months"] - baseline["runway_months"], 2)
    return {
        "scenario_type": scenario_type,
        "currency": summary["currency"],
        "baseline": baseline,
        "scenario": scenario,
        "difference": {
            "monthly_outflow_paise": scenario["monthly_outflow_paise"] - baseline["monthly_outflow_paise"],
            "runway_months": runway_difference,
            "cash_90d_paise": scenario["cash_90d_paise"] - baseline["cash_90d_paise"],
        },
        "assumptions": parameters,
        "classification": "forecast",
        "disclaimer": "This is a deterministic planning scenario, not a guaranteed outcome.",
    }
