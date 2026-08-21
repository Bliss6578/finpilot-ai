from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AuthContext, require_auth
from app.config import Settings, get_settings
from app.database import get_db
from app.models import AuthSession, Business, BusinessMember, RazorpayConnection, User
from app.security import hash_password, hash_token, normalize_email, verify_password


router = APIRouter(prefix="/api/auth", tags=["authentication"])


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=10, max_length=128)
    business_name: str = Field(min_length=2, max_length=160)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=128)


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
        samesite="lax",
        path="/",
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
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
    connection = db.scalar(select(RazorpayConnection).where(RazorpayConnection.business_id == business.id))
    return context_json(user, business, membership, bool(connection and connection.status == "connected"))


@router.post("/login")
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
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
) -> Response:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(token)))
        if session:
            db.delete(session)
            db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
