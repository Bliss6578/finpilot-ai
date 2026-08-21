import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import routes
from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app
from app.models import RazorpayConnection, Refund, Settlement, Transaction, WebhookEvent


def webhook_headers(body: bytes, event_id: str, secret: str) -> dict[str, str]:
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature,
        "X-Razorpay-Event-Id": event_id,
    }


def test_refund_and_settlement_webhooks_are_idempotent_and_tenant_scoped(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(routes, "SessionLocal", session_factory)

    def override_db():
        with Session(engine) as session:
            yield session

    secret = "financial-webhook-secret"
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="development",
        database_url="sqlite+pysqlite:///:memory:",
        razorpay_webhook_secret=secret,
    )
    frontend_headers = {"X-FinPilot-Request": "1"}
    try:
        with TestClient(app) as first_client, TestClient(app) as second_client:
            first_signup = first_client.post(
                "/api/auth/signup",
                headers=frontend_headers,
                json={
                    "full_name": "First Finance Owner",
                    "business_name": "First Finance Business",
                    "email": "first-finance@example.com",
                    "password": "correct horse battery staple",
                },
            )
            second_signup = second_client.post(
                "/api/auth/signup",
                headers=frontend_headers,
                json={
                    "full_name": "Second Finance Owner",
                    "business_name": "Second Finance Business",
                    "email": "second-finance@example.com",
                    "password": "another correct battery staple",
                },
            )
            assert first_signup.status_code == 201
            assert second_signup.status_code == 201
            first_business_id = first_signup.json()["business"]["id"]
            second_business_id = second_signup.json()["business"]["id"]

            now = datetime.now(timezone.utc)
            with Session(engine) as db:
                db.add_all(
                    [
                        RazorpayConnection(
                            business_id=first_business_id,
                            razorpay_account_id="acc_first_finance",
                            status="connected",
                        ),
                        Transaction(
                            business_id=first_business_id,
                            razorpay_payment_id="pay_finance_first",
                            amount_paise=200000,
                            currency="INR",
                            method="card",
                            status="captured",
                            fee_paise=4400,
                            provider_created_at=now,
                            raw_payload={},
                        ),
                        Transaction(
                            business_id=second_business_id,
                            razorpay_payment_id="pay_finance_second",
                            amount_paise=900000,
                            currency="INR",
                            method="upi",
                            status="captured",
                            provider_created_at=now,
                            raw_payload={},
                        ),
                    ]
                )
                db.commit()

            refund_payload = {
                "entity": "event",
                "account_id": "acc_first_finance",
                "event": "refund.processed",
                "payload": {
                    "refund": {
                        "entity": {
                            "id": "rfnd_finance_first",
                            "amount": 50000,
                            "currency": "INR",
                            "payment_id": "pay_finance_first",
                            "status": "processed",
                            "speed_requested": "normal",
                            "speed_processed": "normal",
                            "acquirer_data": {"arn": "arn_finance_first"},
                            "created_at": 1787310000,
                        }
                    }
                },
            }
            refund_body = json.dumps(refund_payload, separators=(",", ":")).encode()
            headers = webhook_headers(refund_body, "event_refund_finance", secret)
            first_delivery = first_client.post("/api/webhooks/razorpay", content=refund_body, headers=headers)
            duplicate_delivery = first_client.post("/api/webhooks/razorpay", content=refund_body, headers=headers)
            assert first_delivery.status_code == 202
            assert first_delivery.json() == {"accepted": True, "duplicate": False}
            assert duplicate_delivery.status_code == 202
            assert duplicate_delivery.json() == {"accepted": True, "duplicate": True}

            settlement_payload = {
                "entity": "event",
                "account_id": "acc_first_finance",
                "event": "settlement.processed",
                "payload": {
                    "settlement": {
                        "entity": {
                            "id": "setl_finance_first",
                            "amount": 145600,
                            "status": "processed",
                            "fees": 0,
                            "tax": 0,
                            "utr": "UTR-FINANCE-FIRST",
                            "created_at": 1787310600,
                        }
                    }
                },
            }
            settlement_body = json.dumps(settlement_payload, separators=(",", ":")).encode()
            settlement_response = first_client.post(
                "/api/webhooks/razorpay",
                content=settlement_body,
                headers=webhook_headers(settlement_body, "event_settlement_finance", secret),
            )
            assert settlement_response.status_code == 202

            first_refunds = first_client.get("/api/refunds")
            first_settlements = first_client.get("/api/settlements")
            second_refunds = second_client.get("/api/refunds")
            second_settlements = second_client.get("/api/settlements")
            assert [item["id"] for item in first_refunds.json()["items"]] == ["rfnd_finance_first"]
            assert [item["id"] for item in first_settlements.json()["items"]] == ["setl_finance_first"]
            assert second_refunds.json()["items"] == []
            assert second_settlements.json()["items"] == []
            assert second_client.get("/api/refunds/rfnd_finance_first").status_code == 404
            assert second_client.get("/api/settlements/setl_finance_first").status_code == 404

            dashboard = first_client.get("/api/dashboard").json()
            assert dashboard["financial_summary"] == {
                "gross_revenue": 2000.0,
                "refund_amount": 500.0,
                "pending_refund_amount": 0.0,
                "razorpay_fees": 44.0,
                "net_revenue": 1456.0,
                "settled_amount": 1456.0,
            }
            assert dashboard["settlement_counts"] == {"pending": 0, "completed": 1, "failed": 0}

            with Session(engine) as db:
                assert db.scalar(select(func.count()).select_from(Refund)) == 1
                assert db.scalar(select(func.count()).select_from(Settlement)) == 1
                assert db.scalar(select(func.count()).select_from(WebhookEvent)) == 2
                assert db.scalar(select(WebhookEvent.status).where(WebhookEvent.event_type == "refund.processed")) == "processed"
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
