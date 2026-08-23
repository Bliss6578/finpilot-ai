from fastapi.testclient import TestClient

from app.main import app


def test_vercel_preview_origin_can_call_auth_api() -> None:
    origin = "https://paymentor-cve71hvfl-ishita22.vercel.app"
    response = TestClient(app).options(
        "/api/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-paymentor-client",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


def test_unrelated_origin_is_rejected() -> None:
    response = TestClient(app).options(
        "/api/auth/login",
        headers={
            "Origin": "https://not-paymentor.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
