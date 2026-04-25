"""add monitor state and webhook columns

Revision ID: 20260405_0002
Revises: 20260404_0001
Create Date: 2026-04-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260405_0002"
down_revision = "20260404_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("monitors", sa.Column("current_state", sa.String(length=16), nullable=False, server_default="UP"))
    op.add_column("monitors", sa.Column("webhook_url", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("monitors", "webhook_url")
    op.drop_column("monitors", "current_state")
