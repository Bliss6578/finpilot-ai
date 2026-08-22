"""operational intelligence and recurring expenses

Revision ID: a82f9c14d6e3
Revises: c1e7a4b29d03
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a82f9c14d6e3"
down_revision: Union[str, Sequence[str], None] = "c1e7a4b29d03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("expenses", sa.Column("recurrence_frequency", sa.String(24), nullable=True))
    op.add_column("expenses", sa.Column("recurrence_end_date", sa.Date(), nullable=True))
    op.add_column("expenses", sa.Column("next_due_date", sa.Date(), nullable=True))
    op.add_column("expenses", sa.Column("parent_expense_id", sa.String(36), sa.ForeignKey("expenses.id", ondelete="SET NULL"), nullable=True))
    op.add_column("expenses", sa.Column("vendor", sa.String(160), nullable=True))
    op.add_column("expenses", sa.Column("notes", sa.String(1000), nullable=True))
    op.create_index("ix_expenses_next_due_date", "expenses", ["next_due_date"])
    op.create_index("ix_expenses_parent_expense_id", "expenses", ["parent_expense_id"])
    op.add_column("approval_requests", sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("approval_requests", sa.Column("execution_result", sa.JSON(), server_default="{}", nullable=False))


def downgrade() -> None:
    op.drop_column("approval_requests", "execution_result")
    op.drop_column("approval_requests", "executed_at")
    op.drop_index("ix_expenses_parent_expense_id", table_name="expenses")
    op.drop_index("ix_expenses_next_due_date", table_name="expenses")
    for column in ("notes", "vendor", "parent_expense_id", "next_due_date", "recurrence_end_date", "recurrence_frequency"):
        op.drop_column("expenses", column)
