"""add multi tenant authentication

Revision ID: ba90e11217f8
Revises: 31cd489353b4
Create Date: 2026-08-21 15:45:23.873947
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ba90e11217f8"
down_revision: Union[str, Sequence[str], None] = "31cd489353b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "businesses",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_businesses_slug", "businesses", ["slug"], unique=True)
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "business_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_members_user", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], name="fk_members_business", ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "business_id", name="uq_member_user_business"),
    )
    op.create_index("ix_business_members_user_id", "business_members", ["user_id"])
    op.create_index("ix_business_members_business_id", "business_members", ["business_id"])
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_sessions_user", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], name="fk_sessions_business", ondelete="CASCADE"),
    )
    op.create_index("ix_auth_sessions_token_hash", "auth_sessions", ["token_hash"], unique=True)
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_business_id", "auth_sessions", ["business_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    op.create_table(
        "razorpay_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.String(length=64), nullable=False),
        sa.Column("razorpay_account_id", sa.String(length=64), nullable=True),
        sa.Column("auth_type", sa.String(length=24), nullable=False),
        sa.Column("mode", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=True),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], name="fk_razorpay_business", ondelete="CASCADE"),
    )
    op.create_index("ix_razorpay_connections_business_id", "razorpay_connections", ["business_id"], unique=True)
    op.create_index("ix_razorpay_connections_razorpay_account_id", "razorpay_connections", ["razorpay_account_id"], unique=True)
    op.create_table(
        "oauth_states",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_oauth_states_user", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], name="fk_oauth_states_business", ondelete="CASCADE"),
    )
    op.create_index("ix_oauth_states_state_hash", "oauth_states", ["state_hash"], unique=True)
    op.create_index("ix_oauth_states_user_id", "oauth_states", ["user_id"])
    op.create_index("ix_oauth_states_business_id", "oauth_states", ["business_id"])
    op.create_index("ix_oauth_states_expires_at", "oauth_states", ["expires_at"])

    op.execute(
        "INSERT INTO businesses (id, name, slug, currency, created_at) "
        "VALUES ('demo-business', 'FinPilot Demo', 'finpilot-demo', 'INR', CURRENT_TIMESTAMP)"
    )
    op.execute(
        "INSERT INTO razorpay_connections "
        "(business_id, auth_type, mode, status, connected_at, updated_at) "
        "VALUES ('demo-business', 'env_api_key', 'test', 'connected', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
    )

    op.add_column("sync_runs", sa.Column("business_id", sa.String(length=64), nullable=True))
    op.execute("UPDATE sync_runs SET business_id = 'demo-business' WHERE business_id IS NULL")
    op.alter_column("sync_runs", "business_id", nullable=False)
    op.create_index("ix_sync_runs_business_id", "sync_runs", ["business_id"])
    op.create_foreign_key("fk_sync_runs_business", "sync_runs", "businesses", ["business_id"], ["id"], ondelete="CASCADE")

    op.create_foreign_key("fk_transactions_business", "transactions", "businesses", ["business_id"], ["id"], ondelete="CASCADE")
    op.drop_index("ix_transactions_razorpay_payment_id", table_name="transactions")
    op.create_index("ix_transactions_razorpay_payment_id", "transactions", ["razorpay_payment_id"])
    op.create_unique_constraint("uq_transaction_business_payment", "transactions", ["business_id", "razorpay_payment_id"])

    op.add_column("webhook_events", sa.Column("business_id", sa.String(length=64), nullable=True))
    op.execute("UPDATE webhook_events SET business_id = 'demo-business' WHERE business_id IS NULL")
    op.alter_column("webhook_events", "business_id", nullable=False)
    op.drop_constraint("uq_webhook_provider_event_id", "webhook_events", type_="unique")
    op.create_index("ix_webhook_events_business_id", "webhook_events", ["business_id"])
    op.create_unique_constraint("uq_webhook_business_event", "webhook_events", ["business_id", "provider_event_id"])
    op.create_foreign_key("fk_webhook_events_business", "webhook_events", "businesses", ["business_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    op.drop_constraint("fk_webhook_events_business", "webhook_events", type_="foreignkey")
    op.drop_constraint("uq_webhook_business_event", "webhook_events", type_="unique")
    op.drop_index("ix_webhook_events_business_id", table_name="webhook_events")
    op.create_unique_constraint("uq_webhook_provider_event_id", "webhook_events", ["provider_event_id"])
    op.drop_column("webhook_events", "business_id")
    op.drop_constraint("fk_transactions_business", "transactions", type_="foreignkey")
    op.drop_constraint("uq_transaction_business_payment", "transactions", type_="unique")
    op.drop_index("ix_transactions_razorpay_payment_id", table_name="transactions")
    op.create_index("ix_transactions_razorpay_payment_id", "transactions", ["razorpay_payment_id"], unique=True)
    op.drop_constraint("fk_sync_runs_business", "sync_runs", type_="foreignkey")
    op.drop_index("ix_sync_runs_business_id", table_name="sync_runs")
    op.drop_column("sync_runs", "business_id")
    op.drop_table("oauth_states")
    op.drop_table("auth_sessions")
    op.drop_table("business_members")
    op.drop_table("razorpay_connections")
    op.drop_table("users")
    op.drop_table("businesses")
