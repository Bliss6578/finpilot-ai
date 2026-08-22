from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("business_id", "mode", "razorpay_payment_id", name="uq_transaction_business_mode_payment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(12), default="test", index=True)
    razorpay_payment_id: Mapped[str] = mapped_column(String(64), index=True)
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    customer_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    method: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    fee_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    tax_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = (
        UniqueConstraint("business_id", "mode", "razorpay_refund_id", name="uq_refund_business_mode_refund"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(12), default="test", index=True)
    razorpay_refund_id: Mapped[str] = mapped_column(String(64), index=True)
    razorpay_payment_id: Mapped[str] = mapped_column(String(64), index=True)
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    status: Mapped[str] = mapped_column(String(32), index=True)
    receipt: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    batch_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    speed_requested: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    speed_processed: Mapped[Optional[str]] = mapped_column(String(24), nullable=True)
    arn: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    provider_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Settlement(Base):
    __tablename__ = "settlements"
    __table_args__ = (
        UniqueConstraint("business_id", "mode", "razorpay_settlement_id", name="uq_settlement_business_mode_settlement"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(12), default="test", index=True)
    razorpay_settlement_id: Mapped[str] = mapped_column(String(64), index=True)
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), index=True)
    fees_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    tax_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    utr: Mapped[Optional[str]] = mapped_column(String(160), nullable=True, index=True)
    provider_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("business_id", "mode", "provider_event_id", name="uq_webhook_business_mode_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(12), default="test", index=True)
    provider_event_id: Mapped[str] = mapped_column(String(160), index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(24), default="received")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(12), default="test", index=True)
    source: Mapped[str] = mapped_column(String(32), default="razorpay")
    status: Mapped[str] = mapped_column(String(24))
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    industry: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    current_cash_paise: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    monthly_budget_paise: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    monthly_fixed_expenses_paise: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    minimum_reserve_paise: Mapped[int] = mapped_column(BigInteger, default=10_000_000)
    target_runway_months: Mapped[float] = mapped_column(Float, default=12.0)
    target_growth_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_tolerance: Mapped[str] = mapped_column(String(24), default="moderate")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BusinessMember(Base):
    __tablename__ = "business_members"
    __table_args__ = (UniqueConstraint("user_id", "business_id", name="uq_member_user_business"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(24), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AccountToken(Base):
    __tablename__ = "account_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(32), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RazorpayConnection(Base):
    __tablename__ = "razorpay_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), unique=True, index=True)
    razorpay_account_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    auth_type: Mapped[str] = mapped_column(String(24), default="oauth")
    mode: Mapped[str] = mapped_column(String(12), default="test")
    status: Mapped[str] = mapped_column(String(24), default="pending")
    access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    access_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    refresh_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    api_key_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    api_key_secret_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    webhook_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    webhook_secret_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OAuthState(Base):
    __tablename__ = "oauth_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    amount_paise: Mapped[int] = mapped_column(BigInteger)
    expense_type: Mapped[str] = mapped_column(String(24), default="operating")
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    expense_date: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DailyFinancialMetric(Base):
    __tablename__ = "daily_financial_metrics"
    __table_args__ = (UniqueConstraint("business_id", "mode", "metric_date", name="uq_daily_metric_business_mode_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(12), default="test", index=True)
    metric_date: Mapped[date] = mapped_column(Date, index=True)
    gross_revenue_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    refunds_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    fees_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    expenses_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    net_cashflow_paise: Mapped[int] = mapped_column(BigInteger, default=0)
    successful_payments: Mapped[int] = mapped_column(Integer, default=0)
    failed_payments: Mapped[int] = mapped_column(Integer, default=0)
    refund_rate: Mapped[float] = mapped_column(Float, default=0.0)
    failure_rate: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class FinancialAlert(Base):
    __tablename__ = "financial_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(12), default="test", index=True)
    alert_type: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(24), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    metric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    baseline_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="unread", index=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class CFOConversation(Base):
    __tablename__ = "cfo_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CFOMessage(Base):
    __tablename__ = "cfo_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("cfo_conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(24))
    content: Mapped[str] = mapped_column(Text)
    structured_content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ForecastSnapshot(Base):
    __tablename__ = "forecast_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(12), default="test", index=True)
    horizon_days: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id", ondelete="CASCADE"), index=True)
    requested_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    action_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(200))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
