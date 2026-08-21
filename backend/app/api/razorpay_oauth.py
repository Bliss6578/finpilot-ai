from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_auth, require_frontend_request
from app.config import Settings, get_settings
from app.database import get_db
from app.models import OAuthState, RazorpayConnection
from app.security import decrypt_secret, encrypt_secret, hash_token


router = APIRouter(prefix="/api/razorpay/oauth", tags=["razorpay-oauth"])


@router.get("/authorize")
def authorize(
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_frontend_request),
) -> dict[str, str]:
    if not settings.razorpay_oauth_configured:
        raise HTTPException(
            status_code=503,
            detail="Razorpay Partner OAuth is not configured yet. Add the Partner client credentials first.",
        )
    raw_state = secrets.token_urlsafe(40)
    db.add(
        OAuthState(
            id=str(uuid.uuid4()),
            state_hash=hash_token(raw_state),
            user_id=context.user.id,
            business_id=context.business.id,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
    )
    db.commit()
    query = urlencode(
        {
            "client_id": settings.razorpay_client_id,
            "response_type": "code",
            "redirect_uri": settings.effective_razorpay_redirect_uri,
            "scope": "read_only",
            "state": raw_state,
        }
    )
    return {"authorization_url": f"https://auth.razorpay.com/authorize?{query}"}


@router.get("/callback")
async def callback(
    code: str = Query(min_length=4),
    state: str = Query(min_length=16),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    oauth_state = db.scalar(select(OAuthState).where(OAuthState.state_hash == hash_token(state)))
    now = datetime.now(timezone.utc)
    expires_at = oauth_state.expires_at if oauth_state is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if oauth_state is None or expires_at is None or expires_at < now:
        raise HTTPException(status_code=400, detail="OAuth state is invalid or expired")
    if not settings.razorpay_oauth_configured:
        raise HTTPException(status_code=503, detail="Razorpay Partner OAuth is not configured")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://auth.razorpay.com/token",
            json={
                "client_id": settings.razorpay_client_id,
                "client_secret": settings.razorpay_client_secret,
                "grant_type": "authorization_code",
                "redirect_uri": settings.effective_razorpay_redirect_uri,
                "code": code,
                "mode": settings.razorpay_oauth_mode,
            },
        )
        if response.is_error:
            raise HTTPException(status_code=502, detail="Razorpay authorization could not be completed")
        payload = response.json()

    connection = db.scalar(
        select(RazorpayConnection).where(RazorpayConnection.business_id == oauth_state.business_id)
    )
    if connection is None:
        connection = RazorpayConnection(business_id=oauth_state.business_id)
        db.add(connection)
    expires_in = int(payload.get("expires_in", 90 * 24 * 60 * 60))
    connection.razorpay_account_id = payload.get("razorpay_account_id")
    connection.auth_type = "oauth"
    connection.mode = "test" if str(payload.get("public_token", "")).startswith("rzp_test_") else "live"
    connection.status = "connected"
    connection.access_token_encrypted = encrypt_secret(payload["access_token"], settings.token_encryption_key)
    connection.refresh_token_encrypted = encrypt_secret(payload["refresh_token"], settings.token_encryption_key)
    connection.access_token_expires_at = now + timedelta(seconds=expires_in)
    connection.refresh_token_expires_at = now + timedelta(days=180)
    connection.connected_at = now
    db.delete(oauth_state)
    db.commit()
    return RedirectResponse(f"{settings.frontend_url.rstrip('/')}/settings?razorpay=connected", status_code=302)


@router.post("/disconnect", status_code=204)
async def disconnect(
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_frontend_request),
) -> None:
    connection = db.scalar(
        select(RazorpayConnection).where(RazorpayConnection.business_id == context.business.id)
    )
    if connection and connection.auth_type == "oauth":
        if connection.access_token_encrypted and settings.razorpay_oauth_configured:
            access_token = decrypt_secret(connection.access_token_encrypted, settings.token_encryption_key)
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    "https://auth.razorpay.com/revoke",
                    json={
                        "client_id": settings.razorpay_client_id,
                        "client_secret": settings.razorpay_client_secret,
                        "token_type_hint": "access_token",
                        "token": access_token,
                    },
                )
                if response.is_error:
                    raise HTTPException(status_code=502, detail="Razorpay access could not be revoked")
        connection.status = "disconnected"
        connection.access_token_encrypted = None
        connection.refresh_token_encrypted = None
        connection.access_token_expires_at = None
        connection.refresh_token_expires_at = None
        db.commit()
