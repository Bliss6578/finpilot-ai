import hashlib
import hmac

from app.services.razorpay import verify_webhook_signature
from app.security import decrypt_secret, encrypt_secret, hash_password, verify_password
from app.config import Settings


def test_webhook_signature_verification() -> None:
    body = b'{"event":"payment.captured"}'
    secret = "test-webhook-secret"
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, signature, secret)
    assert not verify_webhook_signature(body + b" ", signature, secret)


def test_razorpay_list_notes_are_supported() -> None:
    from datetime import datetime, timezone
    from unittest.mock import Mock

    from app.services.razorpay import upsert_payment

    db = Mock()
    db.scalar.return_value = None
    payment = {
        "id": "pay_test",
        "amount": 249900,
        "currency": "INR",
        "status": "captured",
        "captured": True,
        "created_at": int(datetime.now(timezone.utc).timestamp()),
        "notes": [],
    }
    record = upsert_payment(db, payment)
    assert record.customer_name is None
    db.add.assert_called_once_with(record)


def test_password_hash_is_salted_and_verifiable() -> None:
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")
    assert first != second
    assert verify_password("correct horse battery staple", first)
    assert not verify_password("wrong password", first)


def test_oauth_tokens_are_encrypted_at_rest() -> None:
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    encrypted = encrypt_secret("oauth-access-token", key)
    assert "oauth-access-token" not in encrypted
    assert decrypt_secret(encrypted, key) == "oauth-access-token"


def test_host_generated_secret_can_encrypt_oauth_tokens() -> None:
    key = "render-generated-high-entropy-secret"
    encrypted = encrypt_secret("oauth-access-token", key)
    assert decrypt_secret(encrypted, key) == "oauth-access-token"


def test_hosted_postgres_url_uses_psycopg3() -> None:
    settings = Settings(database_url="postgresql://user:pass@db.internal/paymentor")
    assert settings.sqlalchemy_database_url.startswith("postgresql+psycopg://")
    assert Settings(app_env="production").cookie_samesite == "none"


def test_frontend_origin_removes_trailing_slash() -> None:
    settings = Settings(frontend_url="https://paymentor-ai.vercel.app/")
    assert settings.frontend_origin == "https://paymentor-ai.vercel.app"
