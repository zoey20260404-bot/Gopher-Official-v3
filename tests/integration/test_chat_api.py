"""Agent Chat SSE HTTP 契约测试。"""

# ruff: noqa: S106 测试 hash 不是可用凭据。

import json
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from gopher_agent.api.dependencies.auth import get_current_user
from gopher_agent.api.dependencies.chat import get_chat_service
from gopher_agent.main import create_app
from gopher_agent.models.user import User
from gopher_agent.services.chat import ChatEvent


def build_user() -> User:
    user = User(username="zoey", password_hash="hidden-hash")
    user.id = 7
    return user


class StubChatService:
    async def stream(
        self,
        *,
        user_id: int,
        session_id: str,
        message: str,
    ) -> AsyncIterator[ChatEvent]:
        yield ChatEvent("status", {"session_id": session_id, "stage": "thinking"})
        yield ChatEvent("delta", {"content": f"用户{user_id}:{message}"})
        yield ChatEvent("done", {"session_id": session_id})


def parse_sse(body: str) -> list[tuple[str, dict[str, object]]]:
    frames = []
    for frame in body.strip().split("\n\n"):
        lines = frame.splitlines()
        frames.append((lines[0].removeprefix("event: "), json.loads(lines[1][6:])))
    return frames


def test_chat_streams_sse_and_generates_session_id() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = build_user
    app.dependency_overrides[get_chat_service] = StubChatService

    with TestClient(app) as client:
        response = client.post("/api/v1/chat", json={"message": " 查询岗位 "})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"
    events = parse_sse(response.text)
    assert [event for event, _ in events] == ["status", "delta", "done"]
    assert events[0][1]["session_id"] == events[-1][1]["session_id"]
    assert events[1][1]["content"] == "用户7:查询岗位"


def test_chat_preserves_valid_session_and_rejects_blank_message() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = build_user
    app.dependency_overrides[get_chat_service] = StubChatService
    session_id = "0199d418-9f9a-7000-8000-000000000001"

    with TestClient(app) as client:
        success = client.post(
            "/api/v1/chat",
            json={"message": "继续", "session_id": session_id},
        )
        invalid = client.post("/api/v1/chat", json={"message": "   "})

    assert parse_sse(success.text)[0][1]["session_id"] == session_id
    assert invalid.status_code == 422


def test_chat_returns_503_before_stream_when_agent_disabled() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = build_user

    with TestClient(app) as client:
        response = client.post("/api/v1/chat", json={"message": "查询岗位"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Agent 服务尚未启用或配置不完整"}


def test_chat_openapi_declares_sse_and_bearer_security() -> None:
    operation = create_app().openapi()["paths"]["/api/v1/chat"]["post"]

    assert "text/event-stream" in operation["responses"]["200"]["content"]
    assert operation["security"] == [{"HTTPBearer": []}]
