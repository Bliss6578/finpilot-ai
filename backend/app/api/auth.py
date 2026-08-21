from __future__ import annotations

import re
import secrets
import uuid
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_auth, require_frontend_request
from app.config import Settings, get_settings
from app.database import get_db
from app.models import AccountToken, AuthSession, Business, BusinessMember, RazorpayConnection, User
from app.security import hash_password, hash_token, normalize_email, verify_password
from app.services.email import EmailSender, get_email_sender


router = APIRouter(prefix="/api/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=10, max_length=128)
    business_name: str = Field(min_length=2, max_length=160)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class TokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)


class ResetPasswordRequest(TokenRequest):
    new_password: str = Field(min_length=10, max_length=128)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return (slug or "business")[:140]


def context_json(user: User, business: Business, membership: BusinessMember, connected: bool) -> dict:
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "email_verified": user.email_verified,
        },
        "business": {
            "id": business.id,
            "name": business.name,
            "slug": business.slug,
            "currency": business.currency,
            "role": membership.role,
        },
        "razorpay_connected": connected,
    }


def create_session(
    response: Response,
    db: Session,
    settings: Settings,
    user: User,
    business: Business,
) -> None:
    raw_token = secrets.token_urlsafe(48)
    db.add(
        AuthSession(
            id=str(uuid.uuid4()),
            token_hash=hash_token(raw_token),
            user_id=user.id,
            business_id=business.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_days),
        )
    )
    db.commit()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.app_env != "development",
        samesite=settings.cookie_samesite,
        path="/",
    )


def issue_account_token(
    db: Session,
    settings: Settings,
    email_sender: EmailSender,
    user: User,
    purpose: str,
    expires_in: timedelta,
) -> bool:
    now = datetime.now(timezone.utc)
    latest = db.scalar(
        select(AccountToken)
        .where(
            AccountToken.user_id == user.id,
            AccountToken.purpose == purpose,
            AccountToken.used_at.is_(None),
            AccountToken.expires_at > now,
        )
        .order_by(AccountToken.created_at.desc())
    )
    if latest is not None:
        created_at = latest.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if now - created_at < timedelta(seconds=60):
            return False
    db.execute(
        delete(AccountToken).where(
            AccountToken.user_id == user.id,
            AccountToken.purpose == purpose,
            AccountToken.used_at.is_(None),
        )
    )
    raw_token = secrets.token_urlsafe(48)
    record = AccountToken(
        id=str(uuid.uuid4()),
        token_hash=hash_token(raw_token),
        user_id=user.id,
        purpose=purpose,
        expires_at=now + expires_in,
    )
    db.add(record)
    db.commit()
    path = "verify-email" if purpose == "verify_email" else "reset-password"
    try:
        email_sender.send_account_link(
            to=user.email,
            name=user.full_name,
            purpose=purpose,
            url=f"{settings.frontend_origin}/{path}?token={raw_token}",
        )
    except Exception:
        db.delete(record)
        db.commit()
        raise
    return True


def valid_account_token(db: Session, raw_token: str, purpose: str) -> AccountToken:
    record = db.scalar(
        select(AccountToken).where(
            AccountToken.token_hash == hash_token(raw_token),
            AccountToken.purpose == purpose,
            AccountToken.used_at.is_(None),
        )
    )
    if record is None:
        raise HTTPException(status_code=400, detail="This link is invalid or has already been used")
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This link has expired")
    return record


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    email_sender: EmailSender = Depends(get_email_sender),
    _: None = Depends(require_frontend_request),
) -> dict:
    try:
        email = normalize_email(payload.email)
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account already exists for this email")

    is_first_user = (db.scalar(select(func.count()).select_from(User)) or 0) == 0
    business = db.get(Business, "demo-business") if is_first_user else None
    if business is None:
        base_slug = slugify(payload.business_name)
        slug = base_slug
        suffix = 1
        while db.scalar(select(Business.id).where(Business.slug == slug)):
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        business = Business(id=str(uuid.uuid4()), name=payload.business_name.strip(), slug=slug)
        db.add(business)
    elif business.name == "FinPilot Demo":
        business.name = payload.business_name.strip()
        business.slug = slugify(payload.business_name)

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=password_hash,
    )
    membership = BusinessMember(user_id=user.id, business_id=business.id, role="owner")
    db.add(user)
    try:
        # Persist the business and user before the membership so PostgreSQL's
        # foreign-key checks always see both parent records.
        db.flush()
        db.add(membership)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Unable to create this account") from exc
    create_session(response, db, settings, user, business)
    if settings.email_configured:
        try:
            issue_account_token(
                db, settings, email_sender, user, "verify_email", timedelta(hours=24)
            )
        except Exception:
            logger.exception("Unable to send signup verification email")
    connection = db.scalar(select(RazorpayConnection).where(RazorpayConnection.business_id == business.id))
    return context_json(user, business, membership, bool(connection and connection.status == "connected"))


@router.post("/login")
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_frontend_request),
) -> dict:
    try:
        email = normalize_email(payload.email)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    membership = db.scalar(
        select(BusinessMember).where(BusinessMember.user_id == user.id).order_by(BusinessMember.id)
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="No business workspace is assigned")
    business = db.get(Business, membership.business_id)
    if business is None:
        raise HTTPException(status_code=403, detail="Business workspace is unavailable")
    create_session(response, db, settings, user, business)
    connection = db.scalar(select(RazorpayConnection).where(RazorpayConnection.business_id == business.id))
    return context_json(user, business, membership, bool(connection and connection.status == "connected"))


@router.get("/me")
def me(context: AuthContext = Depends(require_auth), db: Session = Depends(get_db)) -> dict:
    connection = db.scalar(
        select(RazorpayConnection).where(RazorpayConnection.business_id == context.business.id)
    )
    return context_json(
        context.user,
        context.business,
        context.membership,
        bool(connection and connection.status == "connected"),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_frontend_request),
) -> Response:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(token)))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.app_env != "development",
        samesite=settings.cookie_samesite,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_frontend_request),
) -> dict:
    if not verify_password(payload.current_password, context.user.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    try:
        context.user.password_hash = hash_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Password changes revoke every existing session. A fresh session is then
    # issued for this browser so the user is not unexpectedly signed out here.
    db.execute(delete(AuthSession).where(AuthSession.user_id == context.user.id))
    db.commit()
    create_session(response, db, settings, context.user, context.business)
    connection = db.scalar(
        select(RazorpayConnection).where(RazorpayConnection.business_id == context.business.id)
    )
    return context_json(
        context.user,
        context.business,
        context.membership,
        bool(connection and connection.status == "connected"),
    )


@router.post("/sessions/revoke-others")
def revoke_other_sessions(
    request: Request,
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_frontend_request),
) -> dict[str, int]:
    raw_token = request.cookies.get(settings.session_cookie_name)
    current_token_hash = hash_token(raw_token) if raw_token else ""
    result = db.execute(
        delete(AuthSession).where(
            AuthSession.user_id == context.user.id,
            AuthSession.token_hash != current_token_hash,
        )
    )
    db.commit()
    return {"revoked_sessions": result.rowcount or 0}


@router.post("/email/verification/request", status_code=status.HTTP_202_ACCEPTED)
def request_email_verification(
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    email_sender: EmailSender = Depends(get_email_sender),
    _: None = Depends(require_frontend_request),
) -> dict[str, str]:
    if context.user.email_verified:
        return {"status": "already_verified"}
    if not settings.email_configured:
        raise HTTPException(status_code=503, detail="Email delivery is not configured")
    try:
        sent = issue_account_token(
            db, settings, email_sender, context.user, "verify_email", timedelta(hours=24)
        )
    except Exception as exc:
        logger.exception("Unable to send verification email")
        raise HTTPException(status_code=502, detail="Unable to send verification email") from exc
    return {"status": "sent" if sent else "recently_sent"}


@router.post("/email/verification/confirm")
def confirm_email_verification(
    payload: TokenRequest,
    context: AuthContext = Depends(require_auth),
    db: Session = Depends(get_db),
    _: None = Depends(require_frontend_request),
) -> dict:
    token = valid_account_token(db, payload.token, "verify_email")
    if token.user_id != context.user.id:
        raise HTTPException(status_code=403, detail="This link belongs to another account")
    token.used_at = datetime.now(timezone.utc)
    context.user.email_verified = True
    db.commit()
    connection = db.scalar(
        select(RazorpayConnection).where(RazorpayConnection.business_id == context.business.id)
    )
    return context_json(
        context.user,
        context.business,
        context.membership,
        bool(connection and connection.status == "connected"),
    )


@router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    email_sender: EmailSender = Depends(get_email_sender),
    _: None = Depends(require_frontend_request),
) -> dict[str, str]:
    if not settings.email_configured:
        raise HTTPException(status_code=503, detail="Email delivery is not configured")
    try:
        email = normalize_email(payload.email)
    except ValueError:
        return {"status": "accepted"}
    user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user is not None:
        try:
            issue_account_token(
                db, settings, email_sender, user, "reset_password", timedelta(hours=1)
            )
        except Exception:
            logger.exception("Unable to send password reset email")
    return {"status": "accepted"}


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    payload: ResetPasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_frontend_request),
) -> Response:
    token = valid_account_token(db, payload.token, "reset_password")
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="This link is invalid")
    try:
        user.password_hash = hash_password(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    now = datetime.now(timezone.utc)
    token.used_at = now
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.execute(
        delete(AccountToken).where(
            AccountToken.user_id == user.id,
            AccountToken.purpose == "reset_password",
            AccountToken.used_at.is_(None),
            AccountToken.id != token.id,
        )
    )
    db.commit()
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        secure=settings.app_env != "development",
        samesite=settings.cookie_samesite,
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
