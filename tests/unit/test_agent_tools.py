"""岗位资格匹配 LangChain tool wrapper 单元测试。"""

import json
from typing import Any, cast

import pytest
from pydantic import BaseModel

from gopher_agent.agents.tools import build_position_match_tool
from gopher_agent.services.exceptions import (
    PositionCandidateLimitExceededError,
    UserProfileNotConfirmedError,
)
from gopher_agent.services.matching import (
    PositionMatchQuery,
    PositionMatchResult,
    PositionMatchService,
)
from gopher_agent.tools.positions import PositionMatchTool


class StubMatchService(PositionMatchService):
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.call: tuple[int, PositionMatchQuery] | None = None

    async def search(self, user_id: int, query: PositionMatchQuery) -> PositionMatchResult:
        if self.error is not None:
            raise self.error
        self.call = (user_id, query)
        return PositionMatchResult(items=[], total=0, page=query.page, page_size=query.page_size)


async def test_match_tool_schema_hides_identity_and_emits_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[dict[str, object]] = []
    monkeypatch.setattr("gopher_agent.agents.tools.get_stream_writer", lambda: events.append)
    service = StubMatchService()
    tool = build_position_match_tool(PositionMatchTool(service, user_id=7))

    result = json.loads(await tool.ainvoke({"province": "广东", "page_size": 5}))

    assert tool.args_schema is not None
    tool_schema = cast(type[BaseModel], tool.args_schema)
    assert "user_id" not in tool_schema.model_fields
    assert "profile" not in tool_schema.model_fields
    assert service.call == (7, PositionMatchQuery(province="广东", page_size=5))
    assert result["total"] == 0
    assert events == [
        {"name": "match_positions", "phase": "started"},
        {"name": "match_positions", "phase": "completed", "result_count": 0},
    ]


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (UserProfileNotConfirmedError(), "user_profile_not_confirmed"),
        (
            PositionCandidateLimitExceededError(2500, 2000),
            "position_candidate_limit_exceeded",
        ),
    ],
)
async def test_match_tool_returns_actionable_business_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    code: str,
) -> None:
    events: list[dict[str, Any]] = []
    monkeypatch.setattr("gopher_agent.agents.tools.get_stream_writer", lambda: events.append)
    tool = build_position_match_tool(PositionMatchTool(StubMatchService(error), user_id=7))

    result = json.loads(await tool.ainvoke({"province": "广东"}))

    assert result["error"]["code"] == code
    assert events[-1] == {"name": "match_positions", "phase": "failed"}
