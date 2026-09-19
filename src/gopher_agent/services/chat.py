"""Agent 对话编排与 transport 无关事件。"""

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol, cast

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)


class StreamingGraphProtocol(Protocol):
    """ChatService 所需的最小 compiled graph 能力。"""

    def astream(
        self,
        input: object,
        config: RunnableConfig,
        *,
        stream_mode: list[str],
    ) -> AsyncIterator[tuple[str, object]]:
        """流式执行 graph。"""
        ...


@dataclass(frozen=True, slots=True)
class ChatEvent:
    """可由 HTTP 层编码成 SSE 的领域事件。"""

    event: str
    data: dict[str, object]


class ChatService:
    """执行 graph，并将 LangGraph stream 转换为稳定事件。"""

    def __init__(self, graph: StreamingGraphProtocol, max_iterations: int) -> None:
        self._graph = graph
        self._max_iterations = max_iterations

    async def stream(
        self,
        *,
        user_id: int,
        session_id: str,
        message: str,
    ) -> AsyncIterator[ChatEvent]:
        """执行一轮对话；流开始后的异常统一转换为安全错误。"""
        yield ChatEvent("status", {"session_id": session_id, "stage": "thinking"})
        config = cast(
            RunnableConfig,
            {
                "configurable": {"thread_id": self.thread_id(user_id, session_id)},
                "recursion_limit": self._max_iterations,
            },
        )
        try:
            async for mode, payload in self._graph.astream(
                {"messages": [HumanMessage(content=message)]},
                config,
                stream_mode=["messages", "custom"],
            ):
                if mode == "custom" and isinstance(payload, dict):
                    yield ChatEvent("tool", dict(payload))
                elif mode == "messages":
                    text = self._message_text(payload)
                    if text:
                        yield ChatEvent("delta", {"content": text})
        except Exception:
            logger.exception("Agent 对话执行失败")
            yield ChatEvent("error", {"code": "agent_execution_failed", "message": "对话处理失败"})
            return
        yield ChatEvent("done", {"session_id": session_id})

    @staticmethod
    def thread_id(user_id: int, session_id: str) -> str:
        """将可信用户身份加入 checkpoint namespace。"""
        return f"user:{user_id}:session:{session_id}"

    @staticmethod
    def _message_text(payload: object) -> str:
        """只提取 AI message chunk 的纯文本内容。"""
        if not isinstance(payload, tuple) or not payload:
            return ""
        message = payload[0]
        if not isinstance(message, (AIMessage, AIMessageChunk)):
            return ""
        return message.text
