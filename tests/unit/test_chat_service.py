"""Agent ChatService 单元测试。"""

from collections.abc import AsyncIterator

from langchain_core.messages import AIMessageChunk, HumanMessageChunk
from langchain_core.runnables import RunnableConfig

from gopher_agent.services.chat import ChatEvent, ChatService


class FakeStreamingGraph:
    """按顺序返回 LangGraph 风格的多模式事件。"""

    def __init__(self, *, fails: bool = False) -> None:
        self.fails = fails
        self.config: RunnableConfig | None = None

    def astream(
        self,
        input: object,
        config: RunnableConfig,
        *,
        stream_mode: list[str],
    ) -> AsyncIterator[tuple[str, object]]:
        self.config = config

        async def events() -> AsyncIterator[tuple[str, object]]:
            if self.fails:
                raise RuntimeError("private provider failure")
            yield "custom", {"name": "query_positions", "phase": "started"}
            yield "messages", (HumanMessageChunk(content="不要输出"), {})
            yield "messages", (AIMessageChunk(content="找到岗位"), {})

        return events()


async def collect(service: ChatService) -> list[ChatEvent]:
    return [
        event
        async for event in service.stream(
            user_id=7,
            session_id="session-1",
            message="查询岗位",
        )
    ]


async def test_chat_service_maps_graph_stream_and_namespaces_thread() -> None:
    graph = FakeStreamingGraph()

    events = await collect(ChatService(graph, max_iterations=8))

    assert [event.event for event in events] == ["status", "tool", "delta", "done"]
    assert events[2].data == {"content": "找到岗位"}
    assert graph.config is not None
    assert graph.config["configurable"]["thread_id"] == "user:7:session:session-1"
    assert ChatService.thread_id(8, "session-1") != ChatService.thread_id(7, "session-1")


async def test_chat_service_sanitizes_stream_error() -> None:
    events = await collect(ChatService(FakeStreamingGraph(fails=True), max_iterations=8))

    assert [event.event for event in events] == ["status", "error"]
    assert events[-1].data == {
        "code": "agent_execution_failed",
        "message": "对话处理失败",
    }
    assert "private" not in str(events[-1].data)
