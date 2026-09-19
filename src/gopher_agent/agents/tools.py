"""LangGraph 可注册的白名单工具。"""

import json
from dataclasses import asdict

from langchain_core.tools import BaseTool, StructuredTool
from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field

from gopher_agent.tools.positions import PositionQueryTool


class PositionToolInput(BaseModel):
    """限制模型可以提交的岗位查询参数。"""

    exam_type: str | None = Field(default=None, max_length=20)
    year: int | None = Field(default=None, ge=2000, le=2100)
    province: str | None = Field(default=None, max_length=50)
    city: str | None = Field(default=None, max_length=100)
    keyword: str | None = Field(default=None, max_length=255)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=5, ge=1, le=10)


def build_position_tool(adapter: PositionQueryTool) -> BaseTool:
    """把领域 adapter 包装为带输入 schema 和 stream event 的 LangChain tool。"""

    async def query_positions(**arguments: object) -> str:
        writer = get_stream_writer()
        writer({"name": PositionQueryTool.name, "phase": "started"})
        query = PositionToolInput.model_validate(arguments)
        result = await adapter.invoke(**query.model_dump())
        writer(
            {
                "name": PositionQueryTool.name,
                "phase": "completed",
                "result_count": len(result.items),
            }
        )
        return json.dumps(asdict(result), ensure_ascii=False)

    return StructuredTool.from_function(
        coroutine=query_positions,
        name=PositionQueryTool.name,
        description=PositionQueryTool.description,
        args_schema=PositionToolInput,
    )
