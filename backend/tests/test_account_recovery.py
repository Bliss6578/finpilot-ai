import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app
from app.models import AccountToken, User
from app.security import hash_token
from app.services.email import get_email_sender


class FakeEmailSender:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def send_account_link(self, **message: str) -> None:
        self.messages.append(message)


def token_from(url: str) -> str:
    return parse_qs(urlparse(url).query)["token"][0]


def test_email_verification_and_password_reset_are_single_use() -> None:
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
    sender = FakeEmailSender()
    settings = Settings(
        app_env="development",
        database_url="sqlite+pysqlite:///:memory:",
        frontend_url="http://localhost:3000/",
        resend_api_key="re_test_key",
        email_from="Paymentor <onboarding@resend.dev>",
    )

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_email_sender] = lambda: sender
    headers = {"X-Paymentor-Request": "1"}
    try:
        with TestClient(app) as client, TestClient(app) as second_device:
            signup = client.post(
                "/api/auth/signup",
                headers=headers,
                json={
                    "full_name": "Recovery Owner",
                    "business_name": "Recovery Business",
                    "email": "recovery@example.com",
                    "password": "correct horse battery staple",
                },
            )
            assert signup.status_code == 201
            assert sender.messages[-1]["purpose"] == "verify_email"
            verify_token = token_from(sender.messages[-1]["url"])
            verification = client.post(
                "/api/auth/email/verification/confirm",
                headers=headers,
                json={"token": verify_token},
            )
            assert verification.status_code == 200
            assert verification.json()["user"]["email_verified"] is True
            assert client.post(
                "/api/auth/email/verification/confirm",
                headers=headers,
                json={"token": verify_token},
            ).status_code == 400

            assert second_device.post(
                "/api/auth/login",
                headers=headers,
                json={
                    "email": "recovery@example.com",
                    "password": "correct horse battery staple",
                },
            ).status_code == 200

            expired_raw_token = "expired-token-" + "x" * 40
            with Session(engine) as session:
                user = session.scalar(select(User).where(User.email == "recovery@example.com"))
                assert user is not None
                session.add(
                    AccountToken(
                        id=str(uuid.uuid4()),
                        token_hash=hash_token(expired_raw_token),
                        user_id=user.id,
                        purpose="reset_password",
                        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                    )
                )
                session.commit()
            expired = client.post(
                "/api/auth/password/reset",
                headers=headers,
                json={
                    "token": expired_raw_token,
                    "new_password": "an expired reset battery staple",
                },
            )
            assert expired.status_code == 400
            assert expired.json()["detail"] == "This link has expired"
            forgot = client.post(
                "/api/auth/password/forgot",
                headers=headers,
                json={"email": "recovery@example.com"},
            )
            assert forgot.status_code == 202
            assert forgot.json() == {"status": "accepted"}
            assert sender.messages[-1]["purpose"] == "reset_password"
            reset_token = token_from(sender.messages[-1]["url"])
            reset = client.post(
                "/api/auth/password/reset",
                headers=headers,
                json={
                    "token": reset_token,
                    "new_password": "a newly reset battery staple",
                },
            )
            assert reset.status_code == 204
            assert client.get("/api/auth/me").status_code == 401
            assert second_device.get("/api/auth/me").status_code == 401
            assert client.post(
                "/api/auth/password/reset",
                headers=headers,
                json={
                    "token": reset_token,
                    "new_password": "another reset battery staple",
                },
            ).status_code == 400
            assert client.post(
                "/api/auth/login",
                headers=headers,
                json={
                    "email": "recovery@example.com",
                    "password": "correct horse battery staple",
                },
            ).status_code == 401
            assert client.post(
                "/api/auth/login",
                headers=headers,
                json={
                    "email": "recovery@example.com",
                    "password": "a newly reset battery staple",
                },
            ).status_code == 200
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
