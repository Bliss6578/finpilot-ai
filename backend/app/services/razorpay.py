from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import RazorpayConnection, Refund, Settlement, Transaction
from app.security import decrypt_secret, encrypt_secret


class RazorpayService:
    base_url = "https://api.razorpay.com/v1"

    def __init__(self, settings: Settings, connection: RazorpayConnection | None = None):
        self.auth: tuple[str, str] | None = None
        self.headers: dict[str, str] = {}
        if connection and connection.auth_type == "oauth" and connection.access_token_encrypted:
            token = decrypt_secret(connection.access_token_encrypted, settings.token_encryption_key)
            self.headers["Authorization"] = f"Bearer {token}"
        elif connection and connection.auth_type == "env_api_key" and settings.razorpay_configured:
            self.auth = (settings.razorpay_key_id, settings.razorpay_key_secret)
        else:
            raise ValueError("This business has not connected a Razorpay account")

    async def _fetch_collection(self, path: str, page_size: int = 100) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        skip = 0
        async with httpx.AsyncClient(timeout=20) as client:
            while True:
                response = await client.get(
                    f"{self.base_url}/{path}",
                    params={"count": page_size, "skip": skip},
                    auth=self.auth,
                    headers=self.headers,
                )
                response.raise_for_status()
                page = response.json().get("items", [])
                if not isinstance(page, list):
                    raise ValueError(f"Razorpay returned an invalid {path} collection")
                items.extend(page)
                if len(page) < page_size:
                    return items
                skip += page_size

    async def fetch_payments(self) -> list[dict[str, Any]]:
        return await self._fetch_collection("payments")

    async def fetch_refunds(self) -> list[dict[str, Any]]:
        return await self._fetch_collection("refunds")

    async def fetch_settlements(self) -> list[dict[str, Any]]:
        return await self._fetch_collection("settlements")


async def refresh_oauth_connection(
    db: Session,
    settings: Settings,
    connection: RazorpayConnection,
) -> RazorpayConnection:
    """Refresh an OAuth token shortly before expiry and rotate its refresh token."""
    if connection.auth_type != "oauth":
        return connection
    now = datetime.now(timezone.utc)
    expires_at = connection.access_token_expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is not None and expires_at > now + timedelta(minutes=5):
        return connection
    if not connection.refresh_token_encrypted or not settings.razorpay_oauth_configured:
        raise ValueError("The Razorpay connection must be authorized again")

    refresh_token = decrypt_secret(connection.refresh_token_encrypted, settings.token_encryption_key)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://auth.razorpay.com/token",
            json={
                "client_id": settings.razorpay_client_id,
                "client_secret": settings.razorpay_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        response.raise_for_status()
        payload = response.json()

    expires_in = int(payload.get("expires_in", 90 * 24 * 60 * 60))
    connection.access_token_encrypted = encrypt_secret(payload["access_token"], settings.token_encryption_key)
    connection.refresh_token_encrypted = encrypt_secret(payload["refresh_token"], settings.token_encryption_key)
    connection.access_token_expires_at = now + timedelta(seconds=expires_in)
    connection.refresh_token_expires_at = now + timedelta(days=180)
    db.commit()
    db.refresh(connection)
    return connection


def verify_webhook_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    if not signature or not secret:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def upsert_payment(db: Session, payment: dict[str, Any], business_id: str = "demo-business") -> Transaction:
    payment_id = payment["id"]
    record = db.scalar(
        select(Transaction).where(
            Transaction.business_id == business_id,
            Transaction.razorpay_payment_id == payment_id,
        )
    )
    created_at = datetime.fromtimestamp(payment.get("created_at", 0), tz=timezone.utc)
    captured_at = created_at if payment.get("captured") else None
    notes = payment.get("notes")
    if not isinstance(notes, dict):
        notes = {}
    values = {
        "razorpay_order_id": payment.get("order_id"),
        "customer_name": notes.get("customer_name") or payment.get("contact"),
        "customer_email": payment.get("email"),
        "amount_paise": payment.get("amount", 0),
        "currency": payment.get("currency", "INR"),
        "method": payment.get("method"),
        "status": payment.get("status", "unknown"),
        "fee_paise": payment.get("fee") or 0,
        "tax_paise": payment.get("tax") or 0,
        "captured_at": captured_at,
        "provider_created_at": created_at,
        "raw_payload": payment,
    }
    if record is None:
        record = Transaction(business_id=business_id, razorpay_payment_id=payment_id, **values)
        db.add(record)
    else:
        for key, value in values.items():
            setattr(record, key, value)
    return record


def provider_datetime(entity: dict[str, Any]) -> datetime:
    timestamp = entity.get("created_at")
    if isinstance(timestamp, (int, float)) and timestamp > 0:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return datetime.now(timezone.utc)


def upsert_refund(db: Session, refund: dict[str, Any], business_id: str = "demo-business") -> Refund:
    refund_id = refund["id"]
    payment_id = refund.get("payment_id")
    if not payment_id:
        raise ValueError(f"Refund {refund_id} is missing its payment identifier")
    record = db.scalar(
        select(Refund).where(
            Refund.business_id == business_id,
            Refund.razorpay_refund_id == refund_id,
        )
    )
    acquirer_data = refund.get("acquirer_data")
    if not isinstance(acquirer_data, dict):
        acquirer_data = {}
    values = {
        "razorpay_payment_id": payment_id,
        "amount_paise": refund.get("amount", 0),
        "currency": refund.get("currency") or "INR",
        "status": refund.get("status", "unknown"),
        "receipt": refund.get("receipt"),
        "batch_id": refund.get("batch_id"),
        "speed_requested": refund.get("speed_requested"),
        "speed_processed": refund.get("speed_processed"),
        "arn": acquirer_data.get("arn"),
        "provider_created_at": provider_datetime(refund),
        "raw_payload": refund,
    }
    if record is None:
        record = Refund(business_id=business_id, razorpay_refund_id=refund_id, **values)
        db.add(record)
    else:
        for key, value in values.items():
            setattr(record, key, value)
    return record


def upsert_settlement(
    db: Session,
    settlement: dict[str, Any],
    business_id: str = "demo-business",
) -> Settlement:
    settlement_id = settlement["id"]
    record = db.scalar(
        select(Settlement).where(
            Settlement.business_id == business_id,
            Settlement.razorpay_settlement_id == settlement_id,
        )
    )
    values = {
        "amount_paise": settlement.get("amount", 0),
        "status": settlement.get("status", "unknown"),
        "fees_paise": settlement.get("fees") or 0,
        "tax_paise": settlement.get("tax") or 0,
        "utr": settlement.get("utr"),
        "provider_created_at": provider_datetime(settlement),
        "raw_payload": settlement,
    }
    if record is None:
        record = Settlement(business_id=business_id, razorpay_settlement_id=settlement_id, **values)
        db.add(record)
    else:
        for key, value in values.items():
            setattr(record, key, value)
    return record
