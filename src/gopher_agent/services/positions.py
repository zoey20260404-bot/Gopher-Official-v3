"""岗位检索 Application Service。"""

from dataclasses import dataclass
from typing import Any

from gopher_agent.models.position import Position
from gopher_agent.repositories.protocols import PositionRepositoryProtocol
from gopher_agent.repositories.types import PositionQuery


@dataclass(frozen=True, slots=True)
class PositionItem:
    """与持久化实现解耦的岗位展示数据。"""

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

    @classmethod
    def from_model(cls, position: Position) -> "PositionItem":
        """从 ORM model 复制允许公开的业务字段。"""
        return cls(
            id=position.id,
            exam_type=position.exam_type,
            year=position.year,
            province=position.province,
            city=position.city,
            department=position.department,
            position_name=position.position_name,
            position_code=position.position_code,
            education_req=position.education_req,
            major_req_exact=position.major_req_exact,
            major_req_category=position.major_req_category,
            political_req=position.political_req,
            fresh_graduate_req=position.fresh_graduate_req,
            work_experience_years_req=position.work_experience_years_req,
            gender_req=position.gender_req,
            age_limit=position.age_limit,
            household_registration_req=position.household_registration_req,
            other_restrictions=list(position.other_restrictions),
            remarks=position.remarks,
            score_2025=position.score_2025,
            score_2024=position.score_2024,
            score_latest=position.score_latest,
            score_year=position.score_year,
            applicant_ratio_2025=position.applicant_ratio_2025,
        )


@dataclass(frozen=True, slots=True)
class PositionSearchResult:
    """岗位分页查询结果。"""

    items: list[PositionItem]
    total: int
    page: int
    page_size: int


class PositionSearchService:
    """编排岗位 Repository 并建立稳定的输出边界。"""

    def __init__(self, positions: PositionRepositoryProtocol) -> None:
        self._positions = positions

    async def search(self, query: PositionQuery) -> PositionSearchResult:
        """查询岗位并将 ORM 结果转换为业务 DTO。"""
        positions, total = await self._positions.list(query)
        return PositionSearchResult(
            items=[PositionItem.from_model(position) for position in positions],
            total=total,
            page=query.normalized_page,
            page_size=query.normalized_page_size,
        )
