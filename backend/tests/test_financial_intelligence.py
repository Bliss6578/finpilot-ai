from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app
from app.services.financial_engine import calculate_burn_rate, calculate_net_revenue, calculate_runway, health_score


def test_deterministic_finance_formulas() -> None:
    assert calculate_net_revenue(100_000, 5_000, 2_000, 1_000) == 92_000
    assert calculate_burn_rate(360_000, 3) == 120_000
    assert calculate_runway(1_200_000, 120_000) == 10
    score = health_score(runway_months=12, target_runway=12, growth_percent=5, net_cashflow_paise=50_000, failure_rate=2, refund_rate=1)
    assert 0 <= score["score"] <= 100
    assert score["status"] == "healthy"


def test_profile_expenses_summary_scenario_and_tenant_isolation() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: Settings(app_env="development", database_url="sqlite+pysqlite:///:memory:")
    headers = {"X-FinPilot-Request": "1"}
    try:
        with TestClient(app) as owner, TestClient(app) as stranger:
            owner.post("/api/auth/signup", headers=headers, json={"full_name": "Owner", "business_name": "Alpha", "email": "alpha@example.com", "password": "correct horse battery staple"})
            stranger.post("/api/auth/signup", headers=headers, json={"full_name": "Other", "business_name": "Beta", "email": "beta@example.com", "password": "another correct battery staple"})
            profile = owner.put("/api/v1/settings/business-profile", headers=headers, json={"industry": "Retail", "website": "https://alpha.example", "current_cash": 500000, "monthly_fixed_expenses": 100000, "minimum_reserve": 150000, "target_runway_months": 9, "risk_tolerance": "conservative", "ai_control_mode": "autopilot", "notification_preferences": {"Cash flow risks": False}, "scenario_preferences": {"revenue": 18, "monthly": 75000}})
            assert profile.status_code == 200
            assert profile.json()["current_cash"] == 500000
            assert profile.json()["ai_control_mode"] == "autopilot"
            assert profile.json()["notification_preferences"]["Cash flow risks"] is False
            assert profile.json()["scenario_preferences"]["monthly"] == 75000
            assert stranger.get("/api/v1/settings/business-profile").json()["scenario_preferences"] == {}
            expense = owner.post("/api/v1/expenses", headers=headers, json={"category": "Payroll", "amount": 100000, "expense_type": "payroll", "recurring": True, "expense_date": date.today().isoformat()})
            assert expense.status_code == 201
            assert owner.get("/api/v1/expenses").json()["total"] == 1
            assert stranger.get("/api/v1/expenses").json()["total"] == 0
            summary = owner.get("/api/v1/dashboard/summary").json()
            assert summary["cash"]["current_paise"] == 50_000_000
            assert summary["data_completeness"]["expenses"] is True
            scenario = owner.post("/api/v1/scenarios/simulate", headers=headers, json={"type": "new_hire", "parameters": {"employees": 1, "monthly_salary_paise": 8_000_000}})
            assert scenario.status_code == 200
            assert scenario.json()["scenario"]["monthly_outflow_paise"] > scenario.json()["baseline"]["monthly_outflow_paise"]
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
