"""add refunds and settlements

Revision ID: e8f2c37b9104
Revises: d5a271f17a20
Create Date: 2026-08-21 22:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8f2c37b9104"
down_revision: Union[str, Sequence[str], None] = "d5a271f17a20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refunds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.String(length=64), nullable=False),
        sa.Column("razorpay_refund_id", sa.String(length=64), nullable=False),
        sa.Column("razorpay_payment_id", sa.String(length=64), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("receipt", sa.String(length=160), nullable=True),
        sa.Column("batch_id", sa.String(length=64), nullable=True),
        sa.Column("speed_requested", sa.String(length=24), nullable=True),
        sa.Column("speed_processed", sa.String(length=24), nullable=True),
        sa.Column("arn", sa.String(length=160), nullable=True),
        sa.Column("provider_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], name="fk_refunds_business", ondelete="CASCADE"),
        sa.UniqueConstraint("business_id", "razorpay_refund_id", name="uq_refund_business_refund"),
    )
    op.create_index("ix_refunds_business_id", "refunds", ["business_id"])
    op.create_index("ix_refunds_razorpay_refund_id", "refunds", ["razorpay_refund_id"])
    op.create_index("ix_refunds_razorpay_payment_id", "refunds", ["razorpay_payment_id"])
    op.create_index("ix_refunds_status", "refunds", ["status"])
    op.create_index("ix_refunds_provider_created_at", "refunds", ["provider_created_at"])

    op.create_table(
        "settlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.String(length=64), nullable=False),
        sa.Column("razorpay_settlement_id", sa.String(length=64), nullable=False),
        sa.Column("amount_paise", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("fees_paise", sa.BigInteger(), nullable=False),
        sa.Column("tax_paise", sa.BigInteger(), nullable=False),
        sa.Column("utr", sa.String(length=160), nullable=True),
        sa.Column("provider_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"], name="fk_settlements_business", ondelete="CASCADE"),
        sa.UniqueConstraint("business_id", "razorpay_settlement_id", name="uq_settlement_business_settlement"),
    )
    op.create_index("ix_settlements_business_id", "settlements", ["business_id"])
    op.create_index("ix_settlements_razorpay_settlement_id", "settlements", ["razorpay_settlement_id"])
    op.create_index("ix_settlements_status", "settlements", ["status"])
    op.create_index("ix_settlements_utr", "settlements", ["utr"])
    op.create_index("ix_settlements_provider_created_at", "settlements", ["provider_created_at"])


def downgrade() -> None:
    op.drop_table("settlements")
    op.drop_table("refunds")
