"""岗位查询 API schema。"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from gopher_agent.repositories.types import PositionQuery


class PositionSearchParams(BaseModel):
    """岗位列表 query parameters。"""

    exam_type: str | None = Field(default=None, max_length=20)
    year: int | None = Field(default=None, ge=2000, le=2100)
    province: str | None = Field(default=None, max_length=50)
    city: str | None = Field(default=None, max_length=100)
    keyword: str | None = Field(default=None, max_length=255)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @field_validator("exam_type", "province", "city", "keyword", mode="before")
    @classmethod
    def strip_optional_text(cls, value: object) -> object:
        """过滤条件去除首尾空白，纯空白按未提供处理。"""
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None

    def to_query(self) -> PositionQuery:
        """转换为 transport 无关的 Repository 查询对象。"""
        return PositionQuery(**self.model_dump())


class PositionItemResponse(BaseModel):
    """允许通过 API 公开的岗位业务字段。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    exam_type: str
    year: int
    province: str
    city: str
    department: str
    position_name: str
    position_code: str
    education_req: str
    major_req_exact: str
    major_req_category: str
    political_req: str
    fresh_graduate_req: bool | None
    work_experience_years_req: int
    gender_req: str
    age_limit: int | None
    household_registration_req: str
    other_restrictions: list[Any]
    remarks: str
    score_2025: int | None
    score_2024: int | None
    score_latest: int | None
    score_year: int | None
    applicant_ratio_2025: str


class PositionListResponse(BaseModel):
    """岗位分页响应。"""

    items: list[PositionItemResponse]
    total: int
    page: int
    page_size: int
