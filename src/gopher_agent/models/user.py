"""用户与权威档案 ORM models。"""

from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gopher_agent.models.base import BigIntPrimaryKeyMixin, TimestampMixin


class User(BigIntPrimaryKeyMixin, TimestampMixin):
    """系统登录用户。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (Index("uq_users_username_lower", func.lower(username), unique=True),)


class UserProfile(BigIntPrimaryKeyMixin, TimestampMixin):
    """一名用户唯一的当前权威档案。"""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    profile: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
