"""可供 Agent graph 注册的岗位查询 tool adapter。"""

from typing import ClassVar

from gopher_agent.domain.matching import PositionMatchFilter
from gopher_agent.repositories.types import PositionQuery
from gopher_agent.services.matching import (
    PositionMatchQuery,
    PositionMatchResult,
    PositionMatchService,
)
from gopher_agent.services.positions import PositionSearchResult, PositionSearchService


class PositionQueryTool:
    """将 Agent 输入适配为岗位检索用例，当前不绑定具体 LLM 框架。"""

    name: ClassVar[str] = "query_positions"
    description: ClassVar[str] = "按考试类型、年份、地区和关键词分页查询公务员岗位"

    def __init__(self, service: PositionSearchService) -> None:
        self._service = service

    async def invoke(
        self,
        *,
        exam_type: str | None = None,
        year: int | None = None,
        province: str | None = None,
        city: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PositionSearchResult:
        """使用结构化参数调用共享的岗位检索 Service。"""
        return await self._service.search(
            PositionQuery(
                exam_type=exam_type,
                year=year,
                province=province,
                city=city,
                keyword=keyword,
                page=page,
                page_size=page_size,
            )
        )


class PositionMatchTool:
    """将 Agent 输入适配为当前认证用户的岗位资格匹配用例。"""

    name: ClassVar[str] = "match_positions"
    description: ClassVar[str] = "基于当前用户已确认档案判断公务员岗位是否可能符合"

    def __init__(self, service: PositionMatchService, user_id: int) -> None:
        self._service = service
        self._user_id = user_id

    async def invoke(
        self,
        *,
        exam_type: str | None = None,
        year: int | None = None,
        province: str | None = None,
        city: str | None = None,
        keyword: str | None = None,
        match_status: PositionMatchFilter = PositionMatchFilter.POTENTIAL,
        page: int = 1,
        page_size: int = 5,
    ) -> PositionMatchResult:
        """使用服务端注入的可信 user ID 调用共享匹配 Service。"""
        return await self._service.search(
            self._user_id,
            PositionMatchQuery(
                exam_type=exam_type,
                year=year,
                province=province,
                city=city,
                keyword=keyword,
                match_filter=match_status,
                page=page,
                page_size=page_size,
            ),
        )
