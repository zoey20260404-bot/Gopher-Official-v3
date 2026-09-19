"""可供 Agent graph 注册的岗位查询 tool adapter。"""

from typing import ClassVar

from gopher_agent.repositories.types import PositionQuery
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
