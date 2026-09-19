"""LangGraph 与岗位 tool loop 单元测试。"""

from collections.abc import Callable, Sequence
from typing import Any, cast

from langchain_core.language_models import LanguageModelInput
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver

from gopher_agent.agents.graph import build_position_agent_graph
from gopher_agent.agents.tools import build_position_tool
from gopher_agent.repositories.types import PositionQuery
from gopher_agent.services.chat import ChatService, StreamingGraphProtocol
from gopher_agent.services.positions import PositionSearchService
from gopher_agent.tools.positions import PositionQueryTool


class EmptyPositionRepository:
    """返回空结果以验证真实 tool 调用链。"""

    def __init__(self) -> None:
        self.query: PositionQuery | None = None

    async def list(self, query: PositionQuery) -> tuple[list[Any], int]:
        self.query = query
        return [], 0


class ScriptedChatModel(BaseChatModel):
    """第一次请求 tool，第二次返回最终答案。"""

    responses: list[AIMessage]
    response_index: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted-test-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: object | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        response = self.responses[self.response_index]
        self.response_index += 1
        return ChatResult(generations=[ChatGeneration(message=response)])

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        return self


def build_scripted_model() -> ScriptedChatModel:
    """创建一轮 tool call 后给出最终回答的模型。"""
    return ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "query_positions",
                        "args": {"province": "广东", "page_size": 5},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="暂时没有找到符合条件的岗位。"),
        ]
    )


async def test_graph_executes_position_tool_and_returns_final_message() -> None:
    repository = EmptyPositionRepository()
    tool = build_position_tool(PositionQueryTool(PositionSearchService(repository)))
    model = build_scripted_model()
    graph = build_position_agent_graph(model, tool, InMemorySaver())

    result = await graph.ainvoke(
        {"messages": [("user", "查询广东岗位")]},
        {"configurable": {"thread_id": "test-thread"}},
    )

    assert repository.query == PositionQuery(province="广东", page_size=5)
    assert any(isinstance(message, ToolMessage) for message in result["messages"])
    assert result["messages"][-1].content == "暂时没有找到符合条件的岗位。"


async def test_real_graph_stream_maps_to_chat_events() -> None:
    repository = EmptyPositionRepository()
    tool = build_position_tool(PositionQueryTool(PositionSearchService(repository)))
    graph = build_position_agent_graph(build_scripted_model(), tool, InMemorySaver())
    service = ChatService(cast(StreamingGraphProtocol, graph), max_iterations=8)

    events = [
        event
        async for event in service.stream(
            user_id=7,
            session_id="stream-test",
            message="查询广东岗位",
        )
    ]

    assert [event.event for event in events] == ["status", "tool", "tool", "delta", "done"]
    assert events[-2].data == {"content": "暂时没有找到符合条件的岗位。"}
