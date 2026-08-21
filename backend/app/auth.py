from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models import AuthSession, Business, BusinessMember, User
from app.security import hash_token


@dataclass
class AuthContext:
    user: User
    business: Business
    membership: BusinessMember


def require_frontend_request(x_finpilot_request: str = Header(default="")) -> None:
    """Require a non-simple header so browsers must pass the configured CORS check."""
    if x_finpilot_request != "1":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request verification failed")


def require_auth(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(token)))
    now = datetime.now(timezone.utc)
    expires_at = session.expires_at if session is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if session is None or expires_at is None or expires_at < now:
        if session is not None:
            db.delete(session)
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    user = db.get(User, session.user_id)
    business = db.get(Business, session.business_id)
    membership = db.scalar(
        select(BusinessMember).where(
            BusinessMember.user_id == session.user_id,
            BusinessMember.business_id == session.business_id,
        )
    )
    if user is None or business is None or membership is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return AuthContext(user=user, business=business, membership=membership)
