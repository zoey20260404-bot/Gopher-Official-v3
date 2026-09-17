"""长期记忆 ORM model。"""

from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gopher_agent.models.base import BigIntPrimaryKeyMixin, TimestampMixin


class Memory(BigIntPrimaryKeyMixin, TimestampMixin):
    """用户画像事实或 Agent 经验的向量检索副本。"""

    __tablename__ = "memories"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('session', 'user', 'agent')",
            name="ck_memories_scope",
        ),
        Index("ix_memories_scope_user_agent", "scope", "user_id", "agent_name"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
