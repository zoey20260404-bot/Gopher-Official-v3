"""真实 Redis checkpoint 恢复与租户隔离测试。"""

import os
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.redis.ashallow import AsyncShallowRedisSaver
from langgraph.graph import END, START, MessagesState, StateGraph

from gopher_agent.services.chat import ChatService


async def exercise_checkpoint(redis_url: str) -> None:
    """在同一 thread 恢复历史，同时隔离另一个用户。"""
    async with AsyncShallowRedisSaver.from_conn_string(
        redis_url,
        ttl={"default_ttl": 5, "refresh_on_read": True},
    ) as saver:
        await saver.asetup()

        async def reply(state: MessagesState) -> dict[str, list[BaseMessage]]:
            return {"messages": [AIMessage(content=f"message-count:{len(state['messages'])}")]}

        builder = StateGraph(MessagesState)
        builder.add_node("reply", reply)
        builder.add_edge(START, "reply")
        builder.add_edge("reply", END)
        graph = builder.compile(checkpointer=saver)
        session_id = str(uuid4())
        first_thread = ChatService.thread_id(7, session_id)
        other_thread = ChatService.thread_id(8, session_id)

        first_config: RunnableConfig = {"configurable": {"thread_id": first_thread}}
        other_config: RunnableConfig = {"configurable": {"thread_id": other_thread}}
        first = await graph.ainvoke(
            MessagesState(messages=[HumanMessage(content="第一轮")]),
            first_config,
        )
        second = await graph.ainvoke(
            MessagesState(messages=[HumanMessage(content="第二轮")]),
            first_config,
        )
        isolated = await graph.ainvoke(
            MessagesState(messages=[HumanMessage(content="另一用户")]),
            other_config,
        )

        assert first["messages"][-1].content == "message-count:1"
        assert second["messages"][-1].content == "message-count:3"
        assert isolated["messages"][-1].content == "message-count:1"

        await saver.adelete_thread(first_thread)
        await saver.adelete_thread(other_thread)


@pytest.mark.redis_integration
async def test_redis_checkpoint_restores_and_isolates_threads() -> None:
    """显式启用时验证 Redis shallow saver。"""
    if os.getenv("RUN_REDIS_INTEGRATION") != "1":
        pytest.skip("设置 RUN_REDIS_INTEGRATION=1 后运行 Redis 集成测试")

    await exercise_checkpoint(os.environ["TEST_REDIS_URL"])
