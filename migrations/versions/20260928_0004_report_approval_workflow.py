"""add report approval workflow state

Revision ID: 20260928_0004
Revises: 20260928_0003
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260928_0004"
down_revision: str | None = "20260928_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """增加报告审批状态、请求快照和幂等键。"""
    op.drop_constraint("ck_reports_status", "reports", type_="check")
    op.create_check_constraint(
        "ck_reports_status",
        "reports",
        "status IN ('processing', 'pending_approval', 'completed', 'rejected', 'failed')",
    )
    op.add_column(
        "reports",
        sa.Column(
            "request_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("reports", sa.Column("last_request_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    """恢复报告的初始状态约束。"""
    op.drop_column("reports", "last_request_id")
    op.drop_column("reports", "request_snapshot")
    op.execute(
        "UPDATE reports SET status = 'failed' WHERE status IN ('pending_approval', 'rejected')"
    )
    op.drop_constraint("ck_reports_status", "reports", type_="check")
    op.create_check_constraint(
        "ck_reports_status",
        "reports",
        "status IN ('processing', 'completed', 'failed')",
    )
