"""建立 v1 兼容的核心业务数据模型。

Revision ID: 20260917_0001
Revises:
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "20260917_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column[object]]:
    """返回所有权威业务表共享的时间字段。"""
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    """创建 extension、核心表、约束和索引。"""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "profile", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        *timestamp_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("mode", sa.String(length=20), server_default="beginner", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="parsing", nullable=False),
        sa.Column(
            "profile_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint("mode IN ('beginner', 'advanced')", name="ck_user_sessions_mode"),
        sa.CheckConstraint(
            "status IN ('parsing', 'confirming', 'completed')",
            name="ck_user_sessions_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_user_sessions_user_updated", "user_sessions", ["user_id", "updated_at"])

    op.create_table(
        "positions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("exam_type", sa.String(length=20), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("province", sa.String(length=50), nullable=False),
        sa.Column("city", sa.String(length=100), server_default="", nullable=False),
        sa.Column("department", sa.String(length=255), nullable=False),
        sa.Column("position_name", sa.String(length=255), nullable=False),
        sa.Column("position_code", sa.String(length=100), nullable=False),
        sa.Column("education_req", sa.String(length=100), server_default="不限", nullable=False),
        sa.Column("major_req_exact", sa.Text(), server_default="", nullable=False),
        sa.Column("major_req_category", sa.String(length=255), server_default="", nullable=False),
        sa.Column("political_req", sa.String(length=100), server_default="不限", nullable=False),
        sa.Column("fresh_graduate_req", sa.Boolean(), nullable=True),
        sa.Column("work_experience_years_req", sa.Integer(), server_default="0", nullable=False),
        sa.Column("gender_req", sa.String(length=20), server_default="不限", nullable=False),
        sa.Column("age_limit", sa.Integer(), nullable=True),
        sa.Column("household_registration_req", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "other_restrictions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("remarks", sa.Text(), server_default="", nullable=False),
        sa.Column("score_2025", sa.Integer(), nullable=True),
        sa.Column("score_2024", sa.Integer(), nullable=True),
        sa.Column("score_latest", sa.Integer(), nullable=True),
        sa.Column("score_year", sa.Integer(), nullable=True),
        sa.Column("applicant_ratio_2025", sa.String(length=20), server_default="", nullable=False),
        sa.Column("source_url", sa.Text(), server_default="", nullable=False),
        sa.Column("data_version", sa.String(length=50), server_default="", nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year", "position_code", name="uq_positions_year_code"),
    )
    op.create_index(
        "ix_positions_exam_year_province",
        "positions",
        ["exam_type", "year", "province"],
    )
    op.create_index("ix_positions_major_category", "positions", ["major_req_category"])

    op.create_table(
        "reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column(
            "profile_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("content", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "result", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("status", sa.String(length=20), server_default="processing", nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'failed')", name="ck_reports_status"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id"),
    )
    op.create_index("ix_reports_user_created", "reports", ["user_id", "created_at"])

    op.create_table(
        "favorites",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("position_id", sa.BigInteger(), nullable=False),
        sa.Column("report_id", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=20), server_default="custom", nullable=False),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "category IN ('rush', 'stable', 'safe', 'custom')",
            name="ck_favorites_category",
        ),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.report_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "position_id", name="uq_favorites_user_position"),
    )
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"])

    op.create_table(
        "memories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("agent_name", sa.String(length=64), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(dim=1024), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint("scope IN ('session', 'user', 'agent')", name="ck_memories_scope"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_memories_scope_user_agent",
        "memories",
        ["scope", "user_id", "agent_name"],
    )


def downgrade() -> None:
    """逆序删除本 revision 创建的表，保留共享 vector extension。"""
    op.drop_index("ix_memories_scope_user_agent", table_name="memories")
    op.drop_table("memories")
    op.drop_index("ix_favorites_user_id", table_name="favorites")
    op.drop_table("favorites")
    op.drop_index("ix_reports_user_created", table_name="reports")
    op.drop_table("reports")
    op.drop_index("ix_positions_major_category", table_name="positions")
    op.drop_index("ix_positions_exam_year_province", table_name="positions")
    op.drop_table("positions")
    op.drop_index("ix_user_sessions_user_updated", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_user_profiles_user_id", table_name="user_profiles")
    op.drop_table("user_profiles")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
