"""选岗报告 LangGraph interrupt/resume 单元测试。"""

from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from gopher_agent.agents.report import build_report_graph
from gopher_agent.domain.report import GeneratedReport, ReportApproval, ReportDecision
from gopher_agent.services.report import ReportGraphProtocol


class FakeRunnable:
    """返回固定 structured report。"""

    async def ainvoke(self, input: object) -> object:
        return {
            "title": "广东岗位建议",
            "overview": "基于已确认档案和资格规则生成。",
            "positions": [
                {
                    "position_code": "P1",
                    "summary": "硬条件明确满足。",
                    "action_items": ["核对公告原文"],
                }
            ],
        }


class FakeStructuredModel:
    """记录 graph 使用的 structured output schema。"""

    def __init__(self) -> None:
        self.schema: type[object] | None = None

    def with_structured_output(self, schema: type[object]) -> FakeRunnable:
        self.schema = schema
        return FakeRunnable()


def graph_input() -> dict[str, object]:
    return {
        "report_id": "report-1",
        "profile": {"education": "本科"},
        "candidates": [
            {
                "position_code": "P1",
                "position_name": "一级行政执法员",
                "department": "税务局",
                "exam_type": "国考",
                "year": 2026,
                "province": "广东",
                "city": "广州",
                "match_status": "eligible",
                "missing_profile_fields": [],
                "reasons": [],
                "score_latest": None,
                "score_year": None,
                "applicant_ratio_2025": "",
            }
        ],
    }


async def test_report_graph_interrupts_then_resumes_approved_generation() -> None:
    model = FakeStructuredModel()
    graph = cast(
        ReportGraphProtocol,
        build_report_graph(
            cast(BaseChatModel, cast(Any, model)),
            InMemorySaver(),
        ),
    )
    config = cast(RunnableConfig, {"configurable": {"thread_id": "report-approve"}})

    paused = await graph.ainvoke(graph_input(), config)
    resumed = await graph.ainvoke(
        Command(resume={"decision": "approve", "approved_position_codes": ["P1"]}),
        config,
    )

    assert "__interrupt__" in paused
    assert model.schema is GeneratedReport
    assert resumed["workflow_status"] == "completed"
    generated = GeneratedReport.model_validate(resumed["generated_report"])
    assert generated.positions[0].position_code == "P1"


async def test_report_graph_rejects_without_calling_model() -> None:
    model = FakeStructuredModel()
    graph = cast(
        ReportGraphProtocol,
        build_report_graph(
            cast(BaseChatModel, cast(Any, model)),
            InMemorySaver(),
        ),
    )
    config = cast(RunnableConfig, {"configurable": {"thread_id": "report-reject"}})

    await graph.ainvoke(graph_input(), config)
    resumed = await graph.ainvoke(
        Command(resume={"decision": "reject", "approved_position_codes": []}),
        config,
    )

    approval = ReportApproval.model_validate(resumed["approval"])
    assert approval.decision is ReportDecision.REJECT
    assert "generated_report" not in resumed
    assert model.schema is None
