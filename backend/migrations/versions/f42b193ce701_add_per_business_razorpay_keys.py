"""add per-business Razorpay API and webhook credentials

Revision ID: f42b193ce701
Revises: e8f2c37b9104
Create Date: 2026-08-21 23:05:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f42b193ce701"
down_revision: Union[str, Sequence[str], None] = "e8f2c37b9104"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("razorpay_connections", sa.Column("api_key_id", sa.String(length=80), nullable=True))
    op.add_column("razorpay_connections", sa.Column("api_key_secret_encrypted", sa.Text(), nullable=True))
    op.add_column("razorpay_connections", sa.Column("webhook_token", sa.String(length=64), nullable=True))
    op.add_column("razorpay_connections", sa.Column("webhook_secret_encrypted", sa.Text(), nullable=True))
    op.create_index(
        "ix_razorpay_connections_webhook_token",
        "razorpay_connections",
        ["webhook_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_razorpay_connections_webhook_token", table_name="razorpay_connections")
    op.drop_column("razorpay_connections", "webhook_secret_encrypted")
    op.drop_column("razorpay_connections", "webhook_token")
    op.drop_column("razorpay_connections", "api_key_secret_encrypted")
    op.drop_column("razorpay_connections", "api_key_id")
