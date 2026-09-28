"""Agent Chat dependencies。"""

from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, status

from gopher_agent.agents.graph import build_position_agent_graph
from gopher_agent.agents.runtime import AgentResources
from gopher_agent.agents.tools import build_position_match_tool, build_position_tool
from gopher_agent.api.dependencies.auth import get_current_user
from gopher_agent.api.dependencies.positions import (
    get_position_match_service,
    get_position_search_service,
)
from gopher_agent.models.user import User
from gopher_agent.services.chat import ChatService, StreamingGraphProtocol
from gopher_agent.services.matching import PositionMatchService
from gopher_agent.services.positions import PositionSearchService
from gopher_agent.tools.positions import PositionMatchTool, PositionQueryTool


def get_chat_service(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    positions: Annotated[PositionSearchService, Depends(get_position_search_service)],
    matching: Annotated[PositionMatchService, Depends(get_position_match_service)],
) -> ChatService:
    """将请求级岗位 Service 绑定到共享模型和 checkpointer。"""
    resources = getattr(request.app.state, "agent_resources", None)
    if resources is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent 服务尚未启用或配置不完整",
        )
    typed_resources = cast(AgentResources, resources)
    tools = [
        build_position_tool(PositionQueryTool(positions)),
        build_position_match_tool(PositionMatchTool(matching, current_user.id)),
    ]
    graph = build_position_agent_graph(
        typed_resources.model,
        tools,
        typed_resources.checkpointer,
    )
    return ChatService(cast(StreamingGraphProtocol, graph), typed_resources.max_iterations)
