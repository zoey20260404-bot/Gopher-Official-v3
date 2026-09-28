"""真实 Redis 上的报告 interrupt/resume checkpoint 测试。"""

import os
from typing import Any, cast
from uuid import uuid4

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.redis.ashallow import AsyncShallowRedisSaver
from langgraph.types import Command

from gopher_agent.agents.report import build_report_graph
from gopher_agent.domain.report import GeneratedReport
from gopher_agent.services.report import ReportGraphProtocol


class RedisTestRunnable:
    async def ainvoke(self, input: object) -> object:
        return {
            "title": "测试报告",
            "overview": "仅验证 checkpoint 恢复。",
            "positions": [
                {
                    "position_code": "P1",
                    "summary": "资格规则已通过。",
                    "action_items": ["核对公告"],
                }
            ],
        }


class RedisTestModel:
    def with_structured_output(self, schema: type[object]) -> RedisTestRunnable:
        assert schema is GeneratedReport
        return RedisTestRunnable()


@pytest.mark.redis_integration
async def test_report_interrupt_resumes_from_redis_checkpoint() -> None:
    """显式启用时验证报告 graph 能跨调用恢复。"""
    if os.getenv("RUN_REDIS_INTEGRATION") != "1":
        pytest.skip("设置 RUN_REDIS_INTEGRATION=1 后运行 Redis 集成测试")

    thread_id = f"report-integration:{uuid4()}"
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    async with AsyncShallowRedisSaver.from_conn_string(
        os.environ["TEST_REDIS_URL"],
        ttl={"default_ttl": 5, "refresh_on_read": True},
    ) as saver:
        await saver.asetup()
        graph = cast(
            ReportGraphProtocol,
            build_report_graph(
                cast(BaseChatModel, cast(Any, RedisTestModel())),
                saver,
            ),
        )
        paused = await graph.ainvoke(
            {
                "report_id": "report-1",
                "profile": {"education": "本科"},
                "candidates": [
                    {
                        "position_code": "P1",
                        "position_name": "测试岗位",
                        "department": "测试部门",
                        "exam_type": "国考",
                        "year": 2026,
                        "province": "广东",
                        "city": "广州",
                        "match_status": "eligible",
                    }
                ],
            },
            config,
        )
        resumed = await graph.ainvoke(
            Command(resume={"decision": "approve", "approved_position_codes": ["P1"]}),
            config,
        )

        assert "__interrupt__" in paused
        assert resumed["workflow_status"] == "completed"
        await saver.adelete_thread(thread_id)
