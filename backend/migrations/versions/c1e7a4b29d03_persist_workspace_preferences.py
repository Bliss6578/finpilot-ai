"""persist workspace preferences

Revision ID: c1e7a4b29d03
Revises: 6f0a9d27c1b2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c1e7a4b29d03"
down_revision: Union[str, Sequence[str], None] = "6f0a9d27c1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("ai_control_mode", sa.String(length=24), nullable=False, server_default="advisor"))
    op.add_column("businesses", sa.Column("notification_preferences", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    op.add_column("businesses", sa.Column("scenario_preferences", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))


def downgrade() -> None:
    op.drop_column("businesses", "scenario_preferences")
    op.drop_column("businesses", "notification_preferences")
    op.drop_column("businesses", "ai_control_mode")
