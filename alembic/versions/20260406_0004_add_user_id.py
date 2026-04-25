"""add user_id to monitors

Revision ID: 20260406_0004
Revises: 20260405_0003
Create Date: 2026-04-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260406_0004"
down_revision = "20260405_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default handles any rows that pre-date this migration
    op.add_column(
        "monitors",
        sa.Column(
            "user_id",
            sa.String(255),
            nullable=False,
            server_default="dev_user",
        ),
    )
    op.create_index("ix_monitors_user_id", "monitors", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_monitors_user_id", table_name="monitors")
    op.drop_column("monitors", "user_id")
