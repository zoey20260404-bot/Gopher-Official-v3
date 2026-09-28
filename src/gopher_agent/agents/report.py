"""带人工审批暂停点的选岗报告 LangGraph。"""

import json
from typing import Any, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from gopher_agent.domain.report import (
    GeneratedReport,
    ReportApproval,
    ReportCandidate,
    ReportDecision,
)

REPORT_SYSTEM_PROMPT = """你是公务员选岗报告撰写助手。
只能依据输入中的已确认档案、岗位事实和确定性资格依据生成建议。
不得改变 match_status, 不得编造分数、竞争比例、录取概率或输入中不存在的岗位事实。
每个已批准岗位必须且只能输出一次。uncertain 岗位必须明确指出需要复核的事项。
输出简洁、可执行, 不得调用工具。"""


class ReportGraphState(TypedDict, total=False):
    """报告 graph checkpoint 中保存的可序列化状态。"""

    report_id: str
    profile: dict[str, object]
    candidates: list[dict[str, object]]
    approval: dict[str, object]
    generated_report: dict[str, object]
    workflow_status: str


def build_report_graph(
    model: BaseChatModel,
    checkpointer: BaseCheckpointSaver[Any],
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """构造审批后才执行 LLM 生成的可恢复 workflow。"""

    def human_review(state: ReportGraphState) -> dict[str, object]:
        raw_approval = interrupt(
            {
                "kind": "report_approval",
                "report_id": state["report_id"],
                "candidates": state["candidates"],
            }
        )
        approval = ReportApproval.model_validate(raw_approval)
        return {"approval": approval.model_dump(mode="json")}

    def route_after_review(state: ReportGraphState) -> str:
        approval = ReportApproval.model_validate(state["approval"])
        return approval.decision.value

    async def generate_report(state: ReportGraphState) -> dict[str, object]:
        approval = ReportApproval.model_validate(state["approval"])
        approved = set(approval.approved_position_codes)
        candidates = [
            ReportCandidate.model_validate(candidate)
            for candidate in state["candidates"]
            if candidate.get("position_code") in approved
        ]
        payload = {
            "profile": state["profile"],
            "approved_candidates": [item.model_dump(mode="json") for item in candidates],
        }
        runnable = model.with_structured_output(GeneratedReport)
        generated = await runnable.ainvoke(
            [
                SystemMessage(content=REPORT_SYSTEM_PROMPT),
                HumanMessage(
                    content=json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                ),
            ]
        )
        report = (
            generated
            if isinstance(generated, GeneratedReport)
            else GeneratedReport.model_validate(generated)
        )
        return {
            "generated_report": report.model_dump(mode="json"),
            "workflow_status": "completed",
        }

    builder = StateGraph(ReportGraphState)
    builder.add_node("human_review", human_review)
    builder.add_node("generate_report", generate_report)
    builder.add_edge(START, "human_review")
    builder.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            ReportDecision.APPROVE.value: "generate_report",
            ReportDecision.REJECT.value: END,
        },
    )
    builder.add_edge("generate_report", END)
    return builder.compile(checkpointer=checkpointer, name="position_report")
