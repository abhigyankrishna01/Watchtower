"""create monitors and results tables

Revision ID: 20260404_0001
Revises: 
Create Date: 2026-04-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260404_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "monitors",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False, server_default="GET"),
        sa.Column("headers", sa.JSON(), nullable=True),
        sa.Column("expected_status", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("json_schema", sa.JSON(), nullable=True),
        sa.Column("timeout_seconds", sa.Float(), nullable=True),
        sa.Column("latency_ms_threshold", sa.Integer(), nullable=True),
        sa.Column("schedule_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "check_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("monitor_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.String(length=2048), nullable=True),
        sa.Column("response_sample", sa.JSON(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("check_results")
    op.drop_table("monitors")
