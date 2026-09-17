"""用户业务会话 ORM model。"""

from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gopher_agent.domain.enums import SessionStatus, UserMode
from gopher_agent.models.base import BigIntPrimaryKeyMixin, TimestampMixin


class UserSession(BigIntPrimaryKeyMixin, TimestampMixin):
    """解析与对话会话的权威元数据，不保存原始聊天流水。"""

    __tablename__ = "user_sessions"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('beginner', 'advanced')",
            name="ck_user_sessions_mode",
        ),
        CheckConstraint(
            "status IN ('parsing', 'confirming', 'completed')",
            name="ck_user_sessions_status",
        ),
        Index("ix_user_sessions_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[str] = mapped_column(String(20), default=UserMode.BEGINNER.value, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=SessionStatus.PARSING.value, nullable=False
    )
    profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
