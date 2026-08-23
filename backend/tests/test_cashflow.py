from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Transaction
from app.services.cashflow import load_retail_model


def test_retail_model_artifact_is_auditable() -> None:
    model = load_retail_model()
    assert model["source"]["rows_seen"] == 1_067_371
    assert model["source"]["active_days"] == 604
    assert model["training"]["return_rate"] == 0.07282909
    assert set(model["training"]["weekday_multipliers"]) == {str(index) for index in range(7)}
    assert len(model["limitations"]) == 3


def test_cashflow_uses_only_tenant_financials() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="development",
        database_url="sqlite+pysqlite:///:memory:",
    )
    headers = {"X-Paymentor-Request": "1"}
    try:
        with TestClient(app) as first_client, TestClient(app) as second_client:
            first_signup = first_client.post(
                "/api/auth/signup",
                headers=headers,
                json={
                    "full_name": "Cash Flow Owner",
                    "business_name": "Cash Flow Shop",
                    "email": "cashflow@example.com",
                    "password": "correct horse battery staple",
                },
            )
            second_client.post(
                "/api/auth/signup",
                headers=headers,
                json={
                    "full_name": "Demo Owner",
                    "business_name": "Demo Shop",
                    "email": "cashflow-demo@example.com",
                    "password": "another correct battery staple",
                },
            )
            business_id = first_signup.json()["business"]["id"]

            demo_response = second_client.get("/api/cashflow?history_days=30&forecast_days=7")
            assert demo_response.status_code == 200
            demo = demo_response.json()
            assert demo["data_source"] == "workspace_financials"
            assert demo["summary"]["cash_available"] == 0
            assert len(demo["points"]) == 37

            now = datetime.now(timezone.utc)
            with Session(engine) as db:
                db.add(
                    Transaction(
                        business_id=business_id,
                        mode="test",
                        razorpay_payment_id="pay_cashflow_first",
                        amount_paise=250_000,
                        currency="INR",
                        status="captured",
                        fee_paise=5_500,
                        provider_created_at=now,
                        raw_payload={},
                    )
                )
                db.commit()

            blended_response = first_client.get("/api/cashflow?history_days=30&forecast_days=7")
            assert blended_response.status_code == 200
            blended = blended_response.json()
            assert blended["data_source"] == "workspace_financials"
            assert blended["model"]["tenant_history_days"] == 1
            assert blended["points"][29]["inflow"] == 2500

            with Session(engine) as db:
                for index in range(1, 14):
                    db.add(
                        Transaction(
                            business_id=business_id,
                            mode="test",
                            razorpay_payment_id=f"pay_cashflow_{index}",
                            amount_paise=100_000 + index * 1_000,
                            currency="INR",
                            status="captured",
                            fee_paise=2_200,
                            provider_created_at=now - timedelta(days=index),
                            raw_payload={},
                        )
                    )
                db.commit()

            tenant_response = first_client.get("/api/cashflow?history_days=30&forecast_days=7")
            assert tenant_response.status_code == 200
            tenant = tenant_response.json()
            assert tenant["data_source"] == "workspace_financials"
            assert tenant["model"]["tenant_history_days"] == 14
            assert len(tenant["points"]) == 37
            assert all(point["actual"] is not None for point in tenant["points"][:30])
            assert all(point["forecast"] is not None for point in tenant["points"][30:])
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
