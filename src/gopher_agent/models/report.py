"""选岗报告 ORM model。"""

from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gopher_agent.domain.enums import ReportStatus
from gopher_agent.models.base import BigIntPrimaryKeyMixin, TimestampMixin


class Report(BigIntPrimaryKeyMixin, TimestampMixin):
    """归属用户的冲稳保报告。"""

    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('processing', 'completed', 'failed')",
            name="ck_reports_status",
        ),
        Index("ix_reports_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=ReportStatus.PROCESSING.value, nullable=False
    )
