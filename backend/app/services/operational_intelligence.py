"""Tenant-scoped operational intelligence and safely executable actions."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApprovalRequest, Business, DailyFinancialMetric, Expense, FinancialAlert, Refund, Settlement, Transaction
from app.services.financial_engine import financial_summary, rebuild_daily_metrics
from app.services.scenarios import simulate


def _rupees(paise: int) -> float:
    return round(paise / 100, 2)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _next_date(value: date, frequency: str) -> date:
    if frequency == "weekly":
        return value + timedelta(days=7)
    if frequency == "quarterly":
        months = 3
    elif frequency == "yearly":
        months = 12
    else:
        months = 1
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    import calendar
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


def materialize_recurring_expenses(db: Session, business_id: str, through: date | None = None) -> int:
    """Create due ledger occurrences exactly once and advance each schedule."""
    through = through or date.today()
    schedules = list(db.scalars(select(Expense).where(
        Expense.business_id == business_id,
        Expense.recurring.is_(True),
        Expense.parent_expense_id.is_(None),
        Expense.next_due_date.is_not(None),
        Expense.next_due_date <= through,
    )).all())
    created = 0
    for schedule in schedules:
        while schedule.next_due_date and schedule.next_due_date <= through:
            if schedule.recurrence_end_date and schedule.next_due_date > schedule.recurrence_end_date:
                schedule.next_due_date = None
                break
            due = schedule.next_due_date
            exists = db.scalar(select(Expense.id).where(
                Expense.parent_expense_id == schedule.id,
                Expense.expense_date == due,
            ))
            if not exists:
                db.add(Expense(
                    id=str(uuid4()), business_id=business_id, category=schedule.category,
                    description=schedule.description, amount_paise=schedule.amount_paise,
                    expense_type=schedule.expense_type, recurring=False, expense_date=due,
                    parent_expense_id=schedule.id, vendor=schedule.vendor, notes=schedule.notes,
                ))
                created += 1
            schedule.next_due_date = _next_date(due, schedule.recurrence_frequency or "monthly")
    db.flush()
    return created


def settlement_intelligence(db: Session, business_id: str, mode: str, days: int = 30) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    transactions = list(db.scalars(select(Transaction).where(
        Transaction.business_id == business_id, Transaction.mode == mode,
        Transaction.status == "captured", Transaction.provider_created_at >= start,
    )).all())
    refunds = list(db.scalars(select(Refund).where(
        Refund.business_id == business_id, Refund.mode == mode,
        Refund.status == "processed", Refund.provider_created_at >= start,
    )).all())
    settlements = list(db.scalars(select(Settlement).where(
        Settlement.business_id == business_id, Settlement.mode == mode,
        Settlement.provider_created_at >= start,
    ).order_by(Settlement.provider_created_at)).all())
    expected = sum(t.amount_paise - t.fee_paise - t.tax_paise for t in transactions) - sum(r.amount_paise for r in refunds)
    processed = [s for s in settlements if s.status == "processed"]
    settled = sum(s.amount_paise for s in processed)
    variance = expected - settled
    delays: list[float] = []
    for transaction in transactions:
        captured_at = _aware(transaction.captured_at or transaction.provider_created_at)
        later = next((s for s in processed if _aware(s.provider_created_at) >= captured_at), None)
        if later:
            delays.append((_aware(later.provider_created_at) - captured_at).total_seconds() / 86400)
    stale = [t for t in transactions if (now - _aware(t.captured_at or t.provider_created_at)).days >= 4]
    status = "reconciled" if abs(variance) <= max(expected * .01, 100) else "attention"
    return {
        "period_days": days, "mode": mode, "status": status,
        "expected_net_settlement": _rupees(expected), "settled_amount": _rupees(settled),
        "variance": _rupees(variance), "pending_settlements": sum(s.status != "processed" for s in settlements),
        "average_delay_days": round(sum(delays) / len(delays), 2) if delays else None,
        "maximum_delay_days": round(max(delays), 2) if delays else None,
        "stale_captured_payments": len(stale),
        "limitations": [] if settlements else ["No settlement records are available for this period; variance is provisional."],
        "evidence": {"captured_payments": len(transactions), "refunds": len(refunds), "settlements": len(settlements)},
    }


def revenue_leaks(db: Session, business_id: str, mode: str, days: int = 30) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    transactions = list(db.scalars(select(Transaction).where(
        Transaction.business_id == business_id, Transaction.mode == mode,
        Transaction.provider_created_at >= start,
    )).all())
    refunds = list(db.scalars(select(Refund).where(
        Refund.business_id == business_id, Refund.mode == mode,
        Refund.provider_created_at >= start, Refund.status == "processed",
    )).all())
    failed = [t for t in transactions if t.status == "failed"]
    captured = [t for t in transactions if t.status == "captured"]
    failed_value = sum(t.amount_paise for t in failed)
    refund_value = sum(r.amount_paise for r in refunds)
    fees = sum(t.fee_paise + t.tax_paise for t in captured)
    gross = sum(t.amount_paise for t in captured)
    settlement = settlement_intelligence(db, business_id, mode, days)
    settlement_gap = max(round(settlement["variance"] * 100), 0)
    signals = [
        {"type": "failed_payments", "title": "Failed payment opportunity", "amount": _rupees(failed_value), "count": len(failed), "confidence": "observed", "action": "Review payment failures and retry eligible customers."},
        {"type": "refunds", "title": "Refund erosion", "amount": _rupees(refund_value), "count": len(refunds), "confidence": "observed", "action": "Group refunds by product or reason before changing policy."},
        {"type": "settlement_gap", "title": "Unreconciled settlement gap", "amount": _rupees(settlement_gap), "count": settlement["stale_captured_payments"], "confidence": "provisional" if settlement["limitations"] else "observed", "action": "Reconcile captured payments against processed settlements."},
    ]
    total = failed_value + refund_value + settlement_gap
    return {
        "period_days": days, "mode": mode, "potential_leak": _rupees(total),
        "gross_revenue": _rupees(gross), "fee_rate": round(fees / gross * 100, 2) if gross else 0,
        "signals": signals, "methodology": "Observed failed attempts and refunds plus provisional unreconciled settlements; opportunities are not booked losses.",
    }


def isolation_forest_anomalies(db: Session, business_id: str, mode: str) -> dict[str, Any]:
    rebuild_daily_metrics(db, business_id, mode, 180)
    metrics = list(db.scalars(select(DailyFinancialMetric).where(
        DailyFinancialMetric.business_id == business_id, DailyFinancialMetric.mode == mode,
    ).order_by(DailyFinancialMetric.metric_date)).all())
    rows = [[m.gross_revenue_paise, m.refunds_paise, m.fees_paise, m.expenses_paise, m.net_cashflow_paise, m.failure_rate, m.refund_rate] for m in metrics]
    if len(rows) < 14:
        return {"model": "insufficient_history", "minimum_days": 14, "observations": len(rows), "anomalies": [], "trained": False}
    try:
        from sklearn.ensemble import IsolationForest
        model = IsolationForest(n_estimators=200, contamination="auto", random_state=42)
        labels = model.fit_predict(rows)
        scores = model.decision_function(rows)
        anomalies = [
            {"date": metric.metric_date.isoformat(), "score": round(float(score), 5), "net_cashflow": _rupees(metric.net_cashflow_paise), "failure_rate": metric.failure_rate, "refund_rate": metric.refund_rate}
            for metric, label, score in zip(metrics, labels, scores) if label == -1
        ]
        return {"model": "isolation_forest", "version": "sklearn-200-trees-v1", "observations": len(rows), "anomalies": anomalies[-20:], "trained": True}
    except ImportError:
        return {"model": "unavailable", "observations": len(rows), "anomalies": [], "trained": False, "error": "scikit-learn is not installed"}


def recommendations(db: Session, business_id: str, mode: str) -> dict[str, Any]:
    summary = financial_summary(db, business_id, mode, 30)
    leaks = revenue_leaks(db, business_id, mode, 30)
    settlements = settlement_intelligence(db, business_id, mode, 30)
    anomalies = isolation_forest_anomalies(db, business_id, mode)
    items: list[dict[str, Any]] = []
    failed = next(signal for signal in leaks["signals"] if signal["type"] == "failed_payments")
    if failed["count"]:
        items.append({"id": "recover_failed_payments", "priority": "high", "title": "Recover eligible failed payments", "impact": failed["amount"], "basis": "revenue_leak", "action_type": "create_follow_up", "parameters": {"category": "payment_recovery", "amount": failed["amount"]}})
    if settlements["status"] == "attention":
        items.append({"id": "reconcile_settlements", "priority": "high", "title": "Open settlement reconciliation review", "impact": abs(settlements["variance"]), "basis": "settlement_variance", "action_type": "create_follow_up", "parameters": {"category": "settlement_reconciliation", "amount": abs(settlements["variance"])}})
    reserve = summary["cash"]["minimum_reserve_paise"] / 100
    if summary["forecast"]["summary"]["lowest_balance"] < reserve:
        items.append({"id": "protect_reserve", "priority": "critical", "title": "Increase reserve protection", "impact": reserve - summary["forecast"]["summary"]["lowest_balance"], "basis": "cashflow", "action_type": "update_cash_policy", "parameters": {"minimum_reserve": reserve}})
    if anomalies.get("anomalies"):
        items.append({"id": "review_anomalies", "priority": "medium", "title": "Review unusual financial days", "impact": 0, "basis": "isolation_forest", "action_type": "create_follow_up", "parameters": {"category": "anomaly_review", "count": len(anomalies["anomalies"])}})
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "items": items, "inputs": {"leaks": leaks["potential_leak"], "settlement_status": settlements["status"], "cash_risk": summary["forecast"]["summary"]["risk_level"], "anomaly_model": anomalies["model"]}}


def execute_approved_action(db: Session, approval: ApprovalRequest) -> dict[str, Any]:
    """Execute only allowlisted, reversible FinPilot-internal actions."""
    if approval.action_type == "update_cash_policy":
        business = db.get(Business, approval.business_id)
        reserve = float(approval.parameters.get("minimum_reserve", 0))
        if not business or reserve < 0:
            raise ValueError("Invalid cash policy action")
        business.minimum_reserve_paise = round(reserve * 100)
        return {"executed": True, "resource": "business_cash_policy", "minimum_reserve": reserve}
    if approval.action_type == "create_follow_up":
        alert = FinancialAlert(
            id=str(uuid4()), business_id=approval.business_id, mode=str(approval.parameters.get("mode", "test")),
            alert_type=str(approval.parameters.get("category", "approved_follow_up")), severity="info",
            title=approval.title, description="Approved operational follow-up. No external funds were moved.",
            status="unread", evidence={"approval_id": approval.id, "parameters": approval.parameters},
        )
        db.add(alert)
        return {"executed": True, "resource": "financial_alert", "id": alert.id}
    raise ValueError("This action type is not executable")
