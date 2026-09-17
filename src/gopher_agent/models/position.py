"""公务员岗位 ORM model。"""

from typing import Any

from sqlalchemy import BigInteger, Boolean, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from gopher_agent.models.base import BigIntPrimaryKeyMixin, TimestampMixin


class Position(BigIntPrimaryKeyMixin, TimestampMixin):
    """岗位硬条件、竞争数据及来源元数据。"""

    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("year", "position_code", name="uq_positions_year_code"),
        Index("ix_positions_exam_year_province", "exam_type", "year", "province"),
        Index("ix_positions_major_category", "major_req_category"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    exam_type: Mapped[str] = mapped_column(String(20), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    province: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    position_name: Mapped[str] = mapped_column(String(255), nullable=False)
    position_code: Mapped[str] = mapped_column(String(100), nullable=False)

    education_req: Mapped[str] = mapped_column(String(100), default="不限", nullable=False)
    major_req_exact: Mapped[str] = mapped_column(Text, default="", nullable=False)
    major_req_category: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    political_req: Mapped[str] = mapped_column(String(100), default="不限", nullable=False)
    fresh_graduate_req: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    work_experience_years_req: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gender_req: Mapped[str] = mapped_column(String(20), default="不限", nullable=False)
    age_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    household_registration_req: Mapped[str] = mapped_column(Text, default="", nullable=False)
    other_restrictions: Mapped[list[Any]] = mapped_column(JSONB, default=list, nullable=False)
    remarks: Mapped[str] = mapped_column(Text, default="", nullable=False)

    score_2025: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_2024: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_latest: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applicant_ratio_2025: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    source_url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    data_version: Mapped[str] = mapped_column(String(50), default="", nullable=False)
