import hashlib
import hmac
import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import razorpay_keys, routes
from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app
from app.models import RazorpayConnection, Transaction, WebhookEvent
from app.security import decrypt_secret
from app.services.razorpay import RazorpayService


def signature(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_razorpay_connection_and_ledger_are_shared_across_device_sessions(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    async def fake_validate(_key_id: str, _key_secret: str) -> None:
        return None

    monkeypatch.setattr(razorpay_keys, "validate_api_credentials", fake_validate)

    def override_db():
        with Session(engine) as session:
            yield session

    settings = Settings(
        app_env="development",
        database_url="sqlite+pysqlite:///:memory:",
        token_encryption_key="test-only-high-entropy-encryption-key",
    )
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    headers = {"X-Paymentor-Request": "1"}
    credentials = {
        "email": "two-devices@example.com",
        "password": "correct horse battery staple",
    }
    try:
        with TestClient(app) as laptop, TestClient(app) as phone:
            signup = laptop.post(
                "/api/auth/signup",
                headers=headers,
                json={
                    "full_name": "Two Device Owner",
                    "business_name": "Shared Workspace",
                    **credentials,
                },
            )
            assert signup.status_code == 201
            business_id = signup.json()["business"]["id"]
            connected = laptop.post(
                "/api/razorpay/api-keys/connect",
                headers=headers,
                json={
                    "key_id": "rzp_test_sharedmerchant",
                    "key_secret": "shared-test-secret",
                },
            )
            assert connected.status_code == 200

            now = datetime.now(timezone.utc)
            with Session(engine) as db:
                db.add(
                    Transaction(
                        business_id=business_id,
                        mode="test",
                        razorpay_payment_id="pay_shared_across_devices",
                        amount_paise=250_000,
                        currency="INR",
                        status="captured",
                        provider_created_at=now,
                        raw_payload={},
                    )
                )
                db.commit()

            login = phone.post("/api/auth/login", headers=headers, json=credentials)
            assert login.status_code == 200
            assert login.json()["business"]["id"] == business_id
            assert login.json()["razorpay_connected"] is True
            assert phone.get("/api/razorpay/status").json()["connected"] is True
            ledger = phone.get("/api/transactions").json()
            assert ledger["total"] == 1
            assert ledger["items"][0]["id"] == "pay_shared_across_devices"
            assert ledger["items"][0]["amount"] == 2500
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_owner_can_manage_encrypted_test_keys_and_tenant_webhook(monkeypatch) -> None:
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
    verified: list[tuple[str, str]] = []

    async def fake_validate(key_id: str, key_secret: str) -> None:
        verified.append((key_id, key_secret))

    monkeypatch.setattr(razorpay_keys, "validate_api_credentials", fake_validate)

    def override_db():
        with Session(engine) as session:
            yield session

    encryption_key = "test-only-high-entropy-encryption-key"
    settings = Settings(
        app_env="development",
        database_url="sqlite+pysqlite:///:memory:",
        token_encryption_key=encryption_key,
        render_external_hostname="paymentor-api.example.com",
    )
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    frontend_headers = {"X-Paymentor-Request": "1"}
    try:
        with TestClient(app) as client:
            signup = client.post(
                "/api/auth/signup",
                headers=frontend_headers,
                json={
                    "full_name": "Key Connection Owner",
                    "business_name": "Key Connection Business",
                    "email": "keys@example.com",
                    "password": "correct horse battery staple",
                },
            )
            assert signup.status_code == 201
            business_id = signup.json()["business"]["id"]

            live_key = client.post(
                "/api/razorpay/api-keys/connect",
                headers=frontend_headers,
                json={"key_id": "rzp_live_not_allowed", "key_secret": "live-secret-value"},
            )
            assert live_key.status_code == 422
            assert verified == []

            first_secret = "first-test-secret-value"
            connected = client.post(
                "/api/razorpay/api-keys/connect",
                headers=frontend_headers,
                json={"key_id": "rzp_test_firstmerchant", "key_secret": first_secret},
            )
            assert connected.status_code == 200
            connected_payload = connected.json()
            assert connected_payload["connected"] is True
            assert connected_payload["key_id"] == "rzp_test_firstmerchant"
            assert connected_payload["webhook_url"].startswith(
                "https://paymentor-api.example.com/api/webhooks/razorpay/"
            )
            assert connected_payload["webhook_secret"]
            assert first_secret not in connected.text
            webhook_url = connected_payload["webhook_url"].replace(
                "https://paymentor-api.example.com", ""
            )
            original_webhook_secret = connected_payload["webhook_secret"]

            with Session(engine) as db:
                connection = db.scalar(
                    select(RazorpayConnection).where(RazorpayConnection.business_id == business_id)
                )
                assert connection is not None
                assert connection.auth_type == "api_key"
                assert connection.api_key_secret_encrypted != first_secret
                assert decrypt_secret(connection.api_key_secret_encrypted, encryption_key) == first_secret
                assert decrypt_secret(connection.webhook_secret_encrypted, encryption_key) == original_webhook_secret

            status_response = client.get("/api/razorpay/status")
            assert status_response.status_code == 200
            assert status_response.json()["connection_type"] == "api_key"
            assert status_response.json()["api_key_id"] == "rzp_test_firstmerchant"
            assert status_response.json()["webhook_url"] == connected_payload["webhook_url"]

            updated = client.post(
                "/api/razorpay/api-keys/connect",
                headers=frontend_headers,
                json={
                    "key_id": "rzp_test_firstmerchant",
                    "key_secret": "replacement-test-secret",
                },
            )
            assert updated.status_code == 200
            assert updated.json()["webhook_secret"] is None
            assert updated.json()["webhook_url"] == connected_payload["webhook_url"]
            with Session(engine) as db:
                connection = db.scalar(
                    select(RazorpayConnection).where(RazorpayConnection.business_id == business_id)
                )
                assert connection is not None
                assert RazorpayService(settings, connection).auth == (
                    "rzp_test_firstmerchant",
                    "replacement-test-secret",
                )

            webhook_payload = {
                "entity": "event",
                "event": "refund.processed",
                "payload": {},
            }
            body = json.dumps(webhook_payload, separators=(",", ":")).encode()
            accepted = client.post(
                webhook_url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Razorpay-Event-Id": "event_tenant_key_webhook",
                    "X-Razorpay-Signature": signature(body, original_webhook_secret),
                },
            )
            assert accepted.status_code == 202
            assert accepted.json() == {"accepted": True, "duplicate": False}

            rotated = client.post(
                "/api/razorpay/api-keys/webhook/rotate",
                headers=frontend_headers,
            )
            assert rotated.status_code == 200
            rotated_secret = rotated.json()["webhook_secret"]
            assert rotated_secret != original_webhook_secret
            rejected_old_secret = client.post(
                webhook_url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Razorpay-Event-Id": "event_old_webhook_secret",
                    "X-Razorpay-Signature": signature(body, original_webhook_secret),
                },
            )
            assert rejected_old_secret.status_code == 401
            accepted_new_secret = client.post(
                webhook_url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Razorpay-Event-Id": "event_new_webhook_secret",
                    "X-Razorpay-Signature": signature(body, rotated_secret),
                },
            )
            assert accepted_new_secret.status_code == 202

            with Session(engine) as db:
                assert db.scalar(select(func.count()).select_from(WebhookEvent)) == 2
                assert set(db.scalars(select(WebhookEvent.business_id)).all()) == {business_id}

            disconnected = client.delete(
                "/api/razorpay/api-keys/disconnect",
                headers=frontend_headers,
            )
            assert disconnected.status_code == 204
            assert client.get("/api/razorpay/status").json()["connected"] is False
            assert client.post(
                webhook_url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Razorpay-Event-Id": "event_after_disconnect",
                    "X-Razorpay-Signature": signature(body, rotated_secret),
                },
            ).status_code == 404
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_live_keys_require_confirmation_and_keep_test_and_live_ledgers_separate(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    async def fake_validate(_key_id: str, _key_secret: str) -> None:
        return None

    monkeypatch.setattr(razorpay_keys, "validate_api_credentials", fake_validate)

    def override_db():
        with Session(engine) as session:
            yield session

    settings = Settings(
        app_env="development",
        database_url="sqlite+pysqlite:///:memory:",
        token_encryption_key="test-only-high-entropy-encryption-key",
        render_external_hostname="paymentor-api.example.com",
    )
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    headers = {"X-Paymentor-Request": "1"}
    try:
        with TestClient(app) as client:
            signup = client.post(
                "/api/auth/signup",
                headers=headers,
                json={
                    "full_name": "Live Mode Owner",
                    "business_name": "Live Mode Business",
                    "email": "live-mode@example.com",
                    "password": "correct horse battery staple",
                },
            )
            assert signup.status_code == 201
            business_id = signup.json()["business"]["id"]

            unconfirmed = client.post(
                "/api/razorpay/api-keys/connect",
                headers=headers,
                json={"key_id": "rzp_live_merchant", "key_secret": "live-secret-value"},
            )
            assert unconfirmed.status_code == 422

            live = client.post(
                "/api/razorpay/api-keys/connect",
                headers=headers,
                json={
                    "key_id": "rzp_live_merchant",
                    "key_secret": "live-secret-value",
                    "confirm_live_access": True,
                },
            )
            assert live.status_code == 200
            assert live.json()["mode"] == "live"
            live_webhook_url = live.json()["webhook_url"]
            assert live.json()["webhook_secret"]
            assert client.get("/api/auth/me").json()["razorpay_mode"] == "live"

            now = datetime.now(timezone.utc)
            with Session(engine) as db:
                db.add_all(
                    [
                        Transaction(
                            business_id=business_id,
                            mode="test",
                            razorpay_payment_id="pay_shared_between_modes",
                            amount_paise=10000,
                            currency="INR",
                            method="upi",
                            status="captured",
                            provider_created_at=now,
                            raw_payload={},
                        ),
                        Transaction(
                            business_id=business_id,
                            mode="live",
                            razorpay_payment_id="pay_shared_between_modes",
                            amount_paise=25000,
                            currency="INR",
                            method="card",
                            status="captured",
                            provider_created_at=now,
                            raw_payload={},
                        ),
                    ]
                )
                db.commit()

            live_dashboard = client.get("/api/dashboard").json()
            assert live_dashboard["mode"] == "live"
            assert live_dashboard["revenue"] == 250.0
            assert client.get("/api/transactions").json()["total"] == 1

            test = client.post(
                "/api/razorpay/api-keys/connect",
                headers=headers,
                json={"key_id": "rzp_test_merchant", "key_secret": "test-secret-value"},
            )
            assert test.status_code == 200
            assert test.json()["mode"] == "test"
            assert test.json()["webhook_url"] != live_webhook_url
            assert test.json()["webhook_secret"]
            test_dashboard = client.get("/api/dashboard").json()
            assert test_dashboard["mode"] == "test"
            assert test_dashboard["revenue"] == 100.0
            assert client.get("/api/auth/me").json()["razorpay_mode"] == "test"
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
