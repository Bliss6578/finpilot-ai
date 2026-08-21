from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Refund, Settlement, Transaction


def test_ai_cfo_uses_only_authenticated_workspace_evidence() -> None:
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
    headers = {"X-FinPilot-Request": "1"}
    try:
        with TestClient(app) as owner, TestClient(app) as other_owner:
            signup = owner.post(
                "/api/auth/signup",
                headers=headers,
                json={
                    "full_name": "Grounded Owner",
                    "business_name": "Grounded Shop",
                    "email": "grounded-cfo@example.com",
                    "password": "correct horse battery staple",
                },
            )
            other_owner.post(
                "/api/auth/signup",
                headers=headers,
                json={
                    "full_name": "Other Owner",
                    "business_name": "Other Shop",
                    "email": "other-cfo@example.com",
                    "password": "another correct battery staple",
                },
            )
            business_id = signup.json()["business"]["id"]
            now = datetime.now(timezone.utc)
            with Session(engine) as db:
                db.add_all(
                    [
                        Transaction(
                            business_id=business_id,
                            mode="test",
                            razorpay_payment_id="pay_cfo_1",
                            amount_paise=100_000,
                            currency="INR",
                            status="captured",
                            fee_paise=2_200,
                            provider_created_at=now - timedelta(days=2),
                            raw_payload={},
                        ),
                        Transaction(
                            business_id=business_id,
                            mode="test",
                            razorpay_payment_id="pay_cfo_2",
                            amount_paise=200_000,
                            currency="INR",
                            status="captured",
                            fee_paise=4_400,
                            provider_created_at=now - timedelta(days=3),
                            raw_payload={},
                        ),
                        Transaction(
                            business_id=business_id,
                            mode="test",
                            razorpay_payment_id="pay_cfo_failed",
                            amount_paise=50_000,
                            currency="INR",
                            status="failed",
                            provider_created_at=now - timedelta(days=4),
                            raw_payload={},
                        ),
                        Refund(
                            business_id=business_id,
                            mode="test",
                            razorpay_refund_id="rfnd_cfo_1",
                            razorpay_payment_id="pay_cfo_2",
                            amount_paise=50_000,
                            currency="INR",
                            status="processed",
                            provider_created_at=now - timedelta(days=1),
                            raw_payload={},
                        ),
                        Settlement(
                            business_id=business_id,
                            mode="test",
                            razorpay_settlement_id="setl_cfo_1",
                            amount_paise=200_000,
                            status="processed",
                            provider_created_at=now - timedelta(days=1),
                            raw_payload={},
                        ),
                    ]
                )
                db.commit()

            revenue = owner.post(
                "/api/ai-cfo/ask",
                headers=headers,
                json={"question": "What is my profit and revenue?"},
            )
            assert revenue.status_code == 200
            body = revenue.json()
            assert "₹2,434" in body["answer"]
            assert "not accounting profit" in body["answer"]
            assert all(metric["label"].lower() != "advertising" for metric in body["metrics"])
            assert "advertising" in body["answer"].lower() and "not connected" in body["answer"].lower()
            assert body["evidence"]["business_id"] == business_id
            assert len(body["suggestions"]) >= 3

            refund = owner.post(
                "/api/ai-cfo/ask",
                headers=headers,
                json={"question": "Why are refunds increasing?"},
            ).json()
            assert "₹500" in refund["answer"]
            assert refund["metrics"][0]["value"] == "₹500"

            isolated = other_owner.post(
                "/api/ai-cfo/ask",
                headers=headers,
                json={"question": "What is my revenue?"},
            ).json()
            assert "no synchronized Razorpay activity" in isolated["answer"]
            assert "₹2,434" not in isolated["answer"]
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
