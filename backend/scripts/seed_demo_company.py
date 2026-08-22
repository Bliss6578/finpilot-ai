"""Seed realistic, isolated demo finance history for an existing business.

Usage: python scripts/seed_demo_company.py --business-id BUSINESS_ID --payments 5000
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import random
from uuid import uuid4

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Business, Expense, Refund, Settlement, Transaction
from app.services.financial_engine import rebuild_daily_metrics, refresh_anomaly_alerts


def seed(db: Session, business_id: str, payments: int, seed_value: int = 6578) -> dict[str, int]:
    business = db.get(Business, business_id)
    if business is None:
        raise ValueError("Business does not exist")
    rng = random.Random(seed_value)
    now = datetime.now(timezone.utc)
    transactions: list[Transaction] = []
    refunds: list[Refund] = []
    for index in range(payments):
        days_ago = rng.randrange(0, 180)
        occurred = now - timedelta(days=days_ago, minutes=rng.randrange(0, 1440))
        failure_probability = 0.12 if days_ago == 28 else 0.04
        status = "failed" if rng.random() < failure_probability else "captured"
        amount = rng.randrange(400, 12_000) * 100
        payment_id = f"pay_demo_{business_id[:8]}_{index}"
        transactions.append(Transaction(
            business_id=business_id, mode="test", razorpay_payment_id=payment_id,
            amount_paise=amount, currency=business.currency, method=rng.choice(["upi", "card", "netbanking"]),
            status=status, fee_paise=round(amount * .022) if status == "captured" else 0,
            provider_created_at=occurred, raw_payload={"demo": True},
        ))
        if status == "captured" and rng.random() < .018:
            refunds.append(Refund(
                business_id=business_id, mode="test", razorpay_refund_id=f"rfnd_demo_{business_id[:8]}_{index}",
                razorpay_payment_id=payment_id, amount_paise=round(amount * rng.choice([.25, .5, 1])),
                currency=business.currency, status="processed", provider_created_at=occurred + timedelta(days=rng.randrange(1, 10)),
                raw_payload={"demo": True},
            ))
    db.add_all(transactions + refunds)
    for month in range(6):
        expense_day = date.today().replace(day=1) - timedelta(days=month * 30)
        for category, amount in (("Payroll", 210_000_00), ("Cloud", 32_000_00), ("Marketing", 65_000_00), ("Software", 18_000_00)):
            db.add(Expense(id=str(uuid4()), business_id=business_id, category=category, description="Generated demo expense", amount_paise=amount, expense_type="payroll" if category == "Payroll" else "operating", recurring=True, expense_date=expense_day))
        db.add(Settlement(business_id=business_id, mode="test", razorpay_settlement_id=f"setl_demo_{business_id[:8]}_{month}", amount_paise=750_000_00 + rng.randrange(-80_000_00, 80_000_00), status="processed", provider_created_at=now - timedelta(days=month * 30 + 2), raw_payload={"demo": True}))
    business.current_cash_paise = business.current_cash_paise or 1_200_000_00
    business.monthly_fixed_expenses_paise = business.monthly_fixed_expenses_paise or 325_000_00
    db.flush()
    metric_days = rebuild_daily_metrics(db, business_id, "test", 180)
    alerts = refresh_anomaly_alerts(db, business_id, "test")
    db.commit()
    return {"payments": len(transactions), "refunds": len(refunds), "metric_days": metric_days, "alerts": len(alerts)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--business-id", required=True)
    parser.add_argument("--payments", type=int, default=5000)
    args = parser.parse_args()
    with SessionLocal() as db:
        print(seed(db, args.business_id, max(100, min(args.payments, 20_000))))


if __name__ == "__main__":
    main()
