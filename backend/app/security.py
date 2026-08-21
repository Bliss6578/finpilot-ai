from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 320 or not EMAIL_PATTERN.match(email):
        raise ValueError("Enter a valid email address")
    return email


def hash_password(password: str) -> str:
    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters")
    salt = os.urandom(16)
    digest = Scrypt(salt=salt, length=32, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P).derive(password.encode())
    return "scrypt${}${}${}${}${}".format(
        SCRYPT_N,
        SCRYPT_R,
        SCRYPT_P,
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        decoded_salt = base64.urlsafe_b64decode(salt)
        digest = Scrypt(
            salt=decoded_salt,
            length=32,
            n=int(n),
            r=int(r),
            p=int(p),
        ).derive(
            password.encode()
        )
        return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode(), expected)
    except (TypeError, ValueError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _fernet(key: str) -> Fernet:
    if not key:
        raise ValueError("TOKEN_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode())
    except (TypeError, ValueError):
        # Hosting providers can safely generate an arbitrary high-entropy
        # secret; derive the exact 32-byte URL-safe key Fernet requires.
        derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
        return Fernet(derived)


def encrypt_secret(value: str, key: str) -> str:
    return _fernet(key).encrypt(value.encode()).decode()


def decrypt_secret(value: str, key: str) -> str:
    try:
        return _fernet(key).decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt Razorpay credentials") from exc
