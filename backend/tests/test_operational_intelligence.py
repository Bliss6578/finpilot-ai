from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import ApprovalRequest, Business, Expense, User
from app.services.operational_intelligence import execute_approved_action, materialize_recurring_expenses


def test_recurring_expenses_are_materialized_once_and_approval_is_allowlisted() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        business = Business(id="biz", name="Tenant", slug="tenant")
        user = User(id="usr", email="owner@example.com", full_name="Owner", password_hash="hash")
        db.add_all([business, user])
        db.flush()
        schedule = Expense(id="schedule", business_id="biz", category="Rent", amount_paise=100_000, expense_type="operating", recurring=True, recurrence_frequency="monthly", expense_date=date(2026, 1, 1), next_due_date=date(2026, 2, 1))
        db.add(schedule)
        assert materialize_recurring_expenses(db, "biz", date(2026, 3, 1)) == 2
        assert materialize_recurring_expenses(db, "biz", date(2026, 3, 1)) == 0
        approval = ApprovalRequest(id="approval", business_id="biz", requested_by_user_id="usr", action_type="update_cash_policy", title="Protect reserve", parameters={"minimum_reserve": 250000}, status="approved")
        db.add(approval)
        result = execute_approved_action(db, approval)
        assert result["executed"] is True
        assert business.minimum_reserve_paise == 25_000_000
