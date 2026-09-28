"""岗位检索 Service 与 tool adapter 单元测试。"""

from gopher_agent.domain.matching import PositionMatchFilter
from gopher_agent.models.position import Position
from gopher_agent.repositories.types import PositionQuery
from gopher_agent.services.matching import (
    PositionMatchQuery,
    PositionMatchResult,
    PositionMatchService,
)
from gopher_agent.services.positions import PositionSearchService
from gopher_agent.tools.positions import PositionMatchTool, PositionQueryTool


def build_position() -> Position:
    """创建包含完整公开字段的岗位测试对象。"""
    position = Position(
        exam_type="国考",
        year=2026,
        province="广东",
        city="广州",
        department="税务局",
        position_name="一级行政执法员",
        position_code="001",
        education_req="本科及以上",
        major_req_exact="计算机科学与技术",
        major_req_category="计算机类",
        political_req="不限",
        fresh_graduate_req=True,
        work_experience_years_req=0,
        gender_req="不限",
        age_limit=35,
        household_registration_req="",
        other_restrictions=["通过体检"],
        remarks="测试岗位",
        score_2025=135,
        score_2024=130,
        score_latest=135,
        score_year=2025,
        applicant_ratio_2025="120:1",
        source_url="https://internal.example/position",
        data_version="test",
    )
    position.id = 7
    return position


class FakePositionRepository:
    """记录查询并返回固定岗位。"""

    def __init__(self) -> None:
        self.query: PositionQuery | None = None
        self.position = build_position()

    async def list(self, query: PositionQuery) -> tuple[list[Position], int]:
        self.query = query
        return [self.position], 1


async def test_position_service_maps_orm_to_stable_result() -> None:
    repository = FakePositionRepository()
    service = PositionSearchService(repository)

    result = await service.search(PositionQuery(province="广东", page=2, page_size=10))

    assert repository.query == PositionQuery(province="广东", page=2, page_size=10)
    assert result.total == 1
    assert result.page == 2
    assert result.page_size == 10
    assert result.items[0].position_code == "001"
    assert result.items[0].other_restrictions == ["通过体检"]
    assert result.items[0].other_restrictions is not repository.position.other_restrictions
    assert not hasattr(result.items[0], "source_url")


async def test_position_tool_has_stable_name_and_reuses_service() -> None:
    repository = FakePositionRepository()
    tool = PositionQueryTool(PositionSearchService(repository))

    result = await tool.invoke(province="广东", keyword="税务", page_size=5)

    assert tool.name == "query_positions"
    assert repository.query == PositionQuery(province="广东", keyword="税务", page_size=5)
    assert result.items[0].department == "税务局"


class StubPositionMatchService(PositionMatchService):
    """记录 tool 注入的可信用户身份。"""

    def __init__(self) -> None:
        self.call: tuple[int, PositionMatchQuery] | None = None

    async def search(self, user_id: int, query: PositionMatchQuery) -> PositionMatchResult:
        self.call = (user_id, query)
        return PositionMatchResult(items=[], total=0, page=query.page, page_size=query.page_size)


async def test_position_match_tool_injects_user_and_has_no_identity_argument() -> None:
    service = StubPositionMatchService()
    tool = PositionMatchTool(service, user_id=7)

    result = await tool.invoke(
        province="广东",
        match_status=PositionMatchFilter.UNCERTAIN,
        page_size=5,
    )

    assert tool.name == "match_positions"
    assert service.call == (
        7,
        PositionMatchQuery(
            province="广东",
            match_filter=PositionMatchFilter.UNCERTAIN,
            page_size=5,
        ),
    )
    assert result.total == 0
