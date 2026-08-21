from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.database import Base, get_db
from app.main import app


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
            assert response.json()["business"]["name"] == "Test Business"
            assert response.json()["business"]["role"] == "owner"
            assert client.get("/api/auth/me").status_code == 200
            assert client.get("/api/transactions").status_code == 200
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
