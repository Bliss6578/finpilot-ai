from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Transaction


def test_signup_session_and_protected_tenant_routes() -> None:
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

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_env="development",
        database_url="sqlite+pysqlite:///:memory:",
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/signup",
                headers={"X-FinPilot-Request": "1"},
                json={
                    "full_name": "Test Owner",
                    "business_name": "Test Business",
                    "email": "owner@example.com",
                    "password": "correct horse battery staple",
                },
            )
            assert response.status_code == 201
            first_business_id = response.json()["business"]["id"]
            assert response.json()["business"]["name"] == "Test Business"
            assert response.json()["business"]["role"] == "owner"
            assert client.get("/api/auth/me").status_code == 200
            assert client.get("/api/transactions").status_code == 200

            with TestClient(app) as other_device:
                login_response = other_device.post(
                    "/api/auth/login",
                    headers={"X-FinPilot-Request": "1"},
                    json={
                        "email": "owner@example.com",
                        "password": "correct horse battery staple",
                    },
                )
                assert login_response.status_code == 200
                revoke_response = client.post(
                    "/api/auth/sessions/revoke-others",
                    headers={"X-FinPilot-Request": "1"},
                )
                assert revoke_response.status_code == 200
                assert revoke_response.json() == {"revoked_sessions": 1}
                assert other_device.get("/api/auth/me").status_code == 401

                assert other_device.post(
                    "/api/auth/login",
                    headers={"X-FinPilot-Request": "1"},
                    json={
                        "email": "owner@example.com",
                        "password": "correct horse battery staple",
                    },
                ).status_code == 200
                password_response = client.post(
                    "/api/auth/change-password",
                    headers={"X-FinPilot-Request": "1"},
                    json={
                        "current_password": "correct horse battery staple",
                        "new_password": "a newer horse battery staple",
                    },
                )
                assert password_response.status_code == 200
                assert client.get("/api/auth/me").status_code == 200
                assert other_device.get("/api/auth/me").status_code == 401
                assert other_device.post(
                    "/api/auth/login",
                    headers={"X-FinPilot-Request": "1"},
                    json={
                        "email": "owner@example.com",
                        "password": "correct horse battery staple",
                    },
                ).status_code == 401
                assert other_device.post(
                    "/api/auth/login",
                    headers={"X-FinPilot-Request": "1"},
                    json={
                        "email": "owner@example.com",
                        "password": "a newer horse battery staple",
                    },
                ).status_code == 200

            with TestClient(app) as tenant_client:
                tenant_signup = tenant_client.post(
                    "/api/auth/signup",
                    headers={"X-FinPilot-Request": "1"},
                    json={
                        "full_name": "Second Owner",
                        "business_name": "Second Business",
                        "email": "second@example.com",
                        "password": "another correct battery staple",
                    },
                )
                assert tenant_signup.status_code == 201
                second_business_id = tenant_signup.json()["business"]["id"]
                now = datetime.now(timezone.utc)
                with Session(engine) as session:
                    session.add_all(
                        [
                            Transaction(
                                business_id=first_business_id,
                                razorpay_payment_id="pay_first_tenant",
                                amount_paise=10000,
                                currency="INR",
                                status="captured",
                                provider_created_at=now,
                                raw_payload={},
                            ),
                            Transaction(
                                business_id=second_business_id,
                                razorpay_payment_id="pay_second_tenant",
                                amount_paise=20000,
                                currency="INR",
                                status="captured",
                                provider_created_at=now,
                                raw_payload={},
                            ),
                        ]
                    )
                    session.commit()

                first_transactions = client.get("/api/transactions").json()
                second_transactions = tenant_client.get("/api/transactions").json()
                assert [item["id"] for item in first_transactions["items"]] == ["pay_first_tenant"]
                assert [item["id"] for item in second_transactions["items"]] == ["pay_second_tenant"]
                assert tenant_client.get("/api/transactions/pay_first_tenant").status_code == 404

            logout_response = client.post("/api/auth/logout", headers={"X-FinPilot-Request": "1"})
            assert logout_response.status_code == 204
            assert client.get("/api/auth/me").status_code == 401

        with TestClient(app) as signed_out_client:
            assert signed_out_client.get("/api/transactions").status_code == 401
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_state_changing_auth_routes_require_verification_header() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "not-used"},
        )
        assert response.status_code == 403
