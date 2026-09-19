"""岗位咨询 LangGraph 定义。"""

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

SYSTEM_PROMPT = """你是公务员岗位咨询助手。需要岗位数据时必须调用 query_positions。
不得编造岗位、分数或竞争比例。回答应简洁。回答必须明确岗位名称和岗位代码。
当前系统只提供岗位检索。遇到范围外问题时说明能力边界。"""


def build_position_agent_graph(
    model: BaseChatModel,
    tool: BaseTool,
    checkpointer: BaseCheckpointSaver[Any],
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """构造 model → tool → model 的显式 ReAct loop。"""
    model_with_tools = model.bind_tools([tool])

    async def call_model(state: MessagesState) -> dict[str, list[BaseMessage]]:
        response = await model_with_tools.ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        )
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode([tool]))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "agent")
    return builder.compile(checkpointer=checkpointer, name="position_advisor")
