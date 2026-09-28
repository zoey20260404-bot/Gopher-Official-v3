"""add user session interview state

Revision ID: 20260928_0003
Revises: 20260919_0002
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260928_0003"
down_revision: str | None = "20260919_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """为档案访谈增加独立的流程状态。"""
    op.add_column(
        "user_sessions",
        sa.Column(
            "interview_state",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """移除档案访谈流程状态。"""
    op.drop_column("user_sessions", "interview_state")
