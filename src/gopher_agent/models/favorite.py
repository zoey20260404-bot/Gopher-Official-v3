"""岗位收藏 ORM model。"""

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from gopher_agent.domain.enums import FavoriteCategory
from gopher_agent.models.base import BigIntPrimaryKeyMixin, TimestampMixin


class Favorite(BigIntPrimaryKeyMixin, TimestampMixin):
    """用户对岗位的唯一收藏关系。"""

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "position_id", name="uq_favorites_user_position"),
        CheckConstraint(
            "category IN ('rush', 'stable', 'safe', 'custom')",
            name="ck_favorites_category",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("positions.id", ondelete="CASCADE"), nullable=False
    )
    report_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("reports.report_id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(
        String(20), default=FavoriteCategory.CUSTOM.value, nullable=False
    )
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
