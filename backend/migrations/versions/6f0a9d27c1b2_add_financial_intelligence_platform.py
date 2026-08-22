"""add financial intelligence platform models

Revision ID: 6f0a9d27c1b2
Revises: 9b7e2a6f4d10
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6f0a9d27c1b2"
down_revision: Union[str, Sequence[str], None] = "9b7e2a6f4d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("industry", sa.String(120), nullable=True))
    op.add_column("businesses", sa.Column("website", sa.String(500), nullable=True))
    op.add_column("businesses", sa.Column("current_cash_paise", sa.BigInteger(), nullable=True))
    op.add_column("businesses", sa.Column("monthly_budget_paise", sa.BigInteger(), nullable=True))
    op.add_column("businesses", sa.Column("monthly_fixed_expenses_paise", sa.BigInteger(), nullable=True))
    op.add_column("businesses", sa.Column("minimum_reserve_paise", sa.BigInteger(), server_default="10000000", nullable=False))
    op.add_column("businesses", sa.Column("target_runway_months", sa.Float(), server_default="12", nullable=False))
    op.add_column("businesses", sa.Column("target_growth_rate", sa.Float(), nullable=True))
    op.add_column("businesses", sa.Column("risk_tolerance", sa.String(24), server_default="moderate", nullable=False))

    op.create_table(
        "expenses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(64), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("expense_type", sa.String(24), server_default="operating", nullable=False),
        sa.Column("recurring", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_expenses_business_id", "expenses", ["business_id"])
    op.create_index("ix_expenses_category", "expenses", ["category"])
    op.create_index("ix_expenses_expense_date", "expenses", ["expense_date"])

    op.create_table(
        "daily_financial_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.String(64), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(12), server_default="test", nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("gross_revenue_paise", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("refunds_paise", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("fees_paise", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("expenses_paise", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("net_cashflow_paise", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("successful_payments", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_payments", sa.Integer(), server_default="0", nullable=False),
        sa.Column("refund_rate", sa.Float(), server_default="0", nullable=False),
        sa.Column("failure_rate", sa.Float(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("business_id", "mode", "metric_date", name="uq_daily_metric_business_mode_date"),
    )
    for column in ("business_id", "mode", "metric_date"):
        op.create_index(f"ix_daily_financial_metrics_{column}", "daily_financial_metrics", [column])

    op.create_table(
        "financial_alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(64), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(12), server_default="test", nullable=False),
        sa.Column("alert_type", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(24), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("status", sa.String(24), server_default="unread", nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("business_id", "mode", "alert_type", "severity", "status", "created_at"):
        op.create_index(f"ix_financial_alerts_{column}", "financial_alerts", [column])

    op.create_table(
        "cfo_conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(64), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cfo_conversations_business_id", "cfo_conversations", ["business_id"])
    op.create_table(
        "cfo_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("cfo_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_content", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cfo_messages_conversation_id", "cfo_messages", ["conversation_id"])
    op.create_index("ix_cfo_messages_created_at", "cfo_messages", ["created_at"])

    op.create_table(
        "forecast_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(64), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(12), server_default="test", nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("business_id", "mode", "generated_at"):
        op.create_index(f"ix_forecast_snapshots_{column}", "forecast_snapshots", [column])

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("business_id", sa.String(64), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(80), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(24), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    for column in ("business_id", "requested_by_user_id", "action_type", "status"):
        op.create_index(f"ix_approval_requests_{column}", "approval_requests", [column])


def downgrade() -> None:
    for table in ("approval_requests", "forecast_snapshots", "cfo_messages", "cfo_conversations", "financial_alerts", "daily_financial_metrics", "expenses"):
        op.drop_table(table)
    for column in ("risk_tolerance", "target_growth_rate", "target_runway_months", "minimum_reserve_paise", "monthly_fixed_expenses_paise", "monthly_budget_paise", "current_cash_paise", "website", "industry"):
        op.drop_column("businesses", column)
