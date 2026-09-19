"""Agent Chat dependencies。"""

from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status

from gopher_agent.agents.graph import build_position_agent_graph
from gopher_agent.agents.runtime import AgentResources
from gopher_agent.agents.tools import build_position_tool
from gopher_agent.api.dependencies.positions import get_position_search_service
from gopher_agent.services.chat import ChatService, StreamingGraphProtocol
from gopher_agent.services.positions import PositionSearchService
from gopher_agent.tools.positions import PositionQueryTool


def get_chat_service(
    request: Request,
    positions: Annotated[PositionSearchService, Depends(get_position_search_service)],
) -> ChatService:
    """将请求级岗位 Service 绑定到共享模型和 checkpointer。"""
    resources = getattr(request.app.state, "agent_resources", None)
    if resources is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent 服务尚未启用或配置不完整",
        )
    typed_resources = cast(AgentResources, resources)
    tool = build_position_tool(PositionQueryTool(positions))
    graph = build_position_agent_graph(
        typed_resources.model,
        tool,
        typed_resources.checkpointer,
    )
    return ChatService(cast(StreamingGraphProtocol, graph), typed_resources.max_iterations)
