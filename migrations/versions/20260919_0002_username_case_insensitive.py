"""增加用户名大小写不敏感唯一约束。

Revision ID: 20260919_0002
Revises: 20260917_0001
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260919_0002"
down_revision: str | Sequence[str] | None = "20260917_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """阻止绕过应用规范化写入大小写重复用户名。"""
    op.create_index(
        "uq_users_username_lower",
        "users",
        [sa.text("lower(username)")],
        unique=True,
    )


def downgrade() -> None:
    """移除大小写不敏感唯一索引。"""
    op.drop_index("uq_users_username_lower", table_name="users")
