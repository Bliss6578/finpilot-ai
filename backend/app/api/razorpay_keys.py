from __future__ import annotations

import secrets
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_auth, require_frontend_request
from app.config import Settings, get_settings
from app.database import get_db
from app.models import RazorpayConnection
from app.security import encrypt_secret
from app.services.razorpay import validate_api_credentials


router = APIRouter(prefix="/api/razorpay/api-keys", tags=["razorpay-api-keys"])


class APIKeyConnectionRequest(BaseModel):
    key_id: str = Field(min_length=12, max_length=80)
    key_secret: SecretStr = Field(min_length=8, max_length=256)


def require_owner(context: AuthContext) -> None:
    if context.membership.role != "owner":
        raise HTTPException(status_code=403, detail="Only the business owner can manage Razorpay credentials")


def webhook_url(settings: Settings, connection: RazorpayConnection) -> str | None:
    if not connection.webhook_token:
        return None
    return f"{settings.backend_origin}/api/webhooks/razorpay/{connection.webhook_token}"


@router.post("/connect")
async def connect_api_keys(
    payload: APIKeyConnectionRequest,
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_frontend_request),
) -> dict:
    require_owner(context)
    key_id = payload.key_id.strip()
    key_secret = payload.key_secret.get_secret_value().strip()
    if not key_id.startswith("rzp_test_"):
        raise HTTPException(
            status_code=422,
            detail="FinPilot beta currently accepts Razorpay Test Mode keys only",
        )
    if not settings.token_encryption_key:
        raise HTTPException(status_code=503, detail="Secure credential encryption is not configured")
    try:
        await validate_api_credentials(key_id, key_secret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Razorpay could not verify these credentials") from exc

    connection = db.scalar(
        select(RazorpayConnection).where(RazorpayConnection.business_id == context.business.id)
    )
    if connection is not None and connection.auth_type == "oauth" and connection.status == "connected":
        raise HTTPException(status_code=409, detail="Disconnect Razorpay OAuth before using API keys")
    if connection is None:
        connection = RazorpayConnection(business_id=context.business.id)
        db.add(connection)

    new_webhook_secret: str | None = None
    if not connection.webhook_token or not connection.webhook_secret_encrypted:
        connection.webhook_token = secrets.token_urlsafe(32)
        new_webhook_secret = secrets.token_hex(32)
        connection.webhook_secret_encrypted = encrypt_secret(new_webhook_secret, settings.token_encryption_key)

    connection.auth_type = "api_key"
    connection.mode = "test"
    connection.status = "connected"
    connection.api_key_id = key_id
    connection.api_key_secret_encrypted = encrypt_secret(key_secret, settings.token_encryption_key)
    connection.razorpay_account_id = None
    connection.access_token_encrypted = None
    connection.refresh_token_encrypted = None
    connection.access_token_expires_at = None
    connection.refresh_token_expires_at = None
    connection.connected_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(connection)
    return {
        "connected": True,
        "mode": "test",
        "key_id": key_id,
        "webhook_url": webhook_url(settings, connection),
        "webhook_secret": new_webhook_secret,
    }


@router.post("/webhook/rotate")
def rotate_webhook_secret(
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_frontend_request),
) -> dict[str, str]:
    require_owner(context)
    connection = db.scalar(
        select(RazorpayConnection).where(
            RazorpayConnection.business_id == context.business.id,
            RazorpayConnection.auth_type == "api_key",
            RazorpayConnection.status == "connected",
        )
    )
    if connection is None:
        raise HTTPException(status_code=409, detail="Connect Razorpay Test Mode keys first")
    if not settings.token_encryption_key:
        raise HTTPException(status_code=503, detail="Secure credential encryption is not configured")
    if not connection.webhook_token:
        connection.webhook_token = secrets.token_urlsafe(32)
    raw_secret = secrets.token_hex(32)
    connection.webhook_secret_encrypted = encrypt_secret(raw_secret, settings.token_encryption_key)
    db.commit()
    return {
        "webhook_url": webhook_url(settings, connection) or "",
        "webhook_secret": raw_secret,
    }


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_api_keys(
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_frontend_request),
) -> None:
    require_owner(context)
    connection = db.scalar(
        select(RazorpayConnection).where(RazorpayConnection.business_id == context.business.id)
    )
    if connection is None or connection.auth_type != "api_key":
        return
    connection.status = "disconnected"
    connection.api_key_id = None
    connection.api_key_secret_encrypted = None
    connection.webhook_token = None
    connection.webhook_secret_encrypted = None
    connection.connected_at = None
    db.commit()
