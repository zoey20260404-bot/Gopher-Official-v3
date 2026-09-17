"""ORM model 的共享字段与类型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from gopher_agent.core.database import Base


class TimestampMixin:
    """统一提供由数据库生成的带时区创建与更新时间。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class BigIntPrimaryKeyMixin(Base):
    """保留与 v1 数据兼容的 bigint 自增主键。"""

    __abstract__ = True

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
