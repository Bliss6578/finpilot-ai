"""add test and live financial record modes

Revision ID: 9b7e2a6f4d10
Revises: f42b193ce701
Create Date: 2026-08-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b7e2a6f4d10"
down_revision: Union[str, Sequence[str], None] = "f42b193ce701"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("transactions", "refunds", "settlements", "webhook_events", "sync_runs"):
        op.add_column(table, sa.Column("mode", sa.String(length=12), server_default="test", nullable=False))
        op.create_index(f"ix_{table}_mode", table, ["mode"])

    op.drop_constraint("uq_transaction_business_payment", "transactions", type_="unique")
    op.create_unique_constraint(
        "uq_transaction_business_mode_payment",
        "transactions",
        ["business_id", "mode", "razorpay_payment_id"],
    )
    op.drop_constraint("uq_refund_business_refund", "refunds", type_="unique")
    op.create_unique_constraint(
        "uq_refund_business_mode_refund",
        "refunds",
        ["business_id", "mode", "razorpay_refund_id"],
    )
    op.drop_constraint("uq_settlement_business_settlement", "settlements", type_="unique")
    op.create_unique_constraint(
        "uq_settlement_business_mode_settlement",
        "settlements",
        ["business_id", "mode", "razorpay_settlement_id"],
    )
    op.drop_constraint("uq_webhook_business_event", "webhook_events", type_="unique")
    op.create_unique_constraint(
        "uq_webhook_business_mode_event",
        "webhook_events",
        ["business_id", "mode", "provider_event_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_webhook_business_mode_event", "webhook_events", type_="unique")
    op.create_unique_constraint("uq_webhook_business_event", "webhook_events", ["business_id", "provider_event_id"])
    op.drop_constraint("uq_settlement_business_mode_settlement", "settlements", type_="unique")
    op.create_unique_constraint(
        "uq_settlement_business_settlement", "settlements", ["business_id", "razorpay_settlement_id"]
    )
    op.drop_constraint("uq_refund_business_mode_refund", "refunds", type_="unique")
    op.create_unique_constraint("uq_refund_business_refund", "refunds", ["business_id", "razorpay_refund_id"])
    op.drop_constraint("uq_transaction_business_mode_payment", "transactions", type_="unique")
    op.create_unique_constraint(
        "uq_transaction_business_payment", "transactions", ["business_id", "razorpay_payment_id"]
    )
    for table in ("sync_runs", "webhook_events", "settlements", "refunds", "transactions"):
        op.drop_index(f"ix_{table}_mode", table_name=table)
        op.drop_column(table, "mode")
