"""Agent SSE 对话接口。"""

import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from gopher_agent.api.dependencies.auth import get_current_user
from gopher_agent.api.dependencies.chat import get_chat_service
from gopher_agent.api.schemas.chat import ChatRequest
from gopher_agent.models.user import User
from gopher_agent.services.chat import ChatEvent, ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


def encode_sse(event: ChatEvent) -> str:
    """把领域事件编码成标准 SSE frame。"""
    data = json.dumps(event.data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event.event}\ndata: {data}\n\n"


@router.post(
    "",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def chat(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    """流式执行一轮经过身份隔离的 Agent 对话。"""
    session_id = str(request.session_id or uuid4())

    async def event_stream() -> AsyncIterator[str]:
        async for event in service.stream(
            user_id=current_user.id,
            session_id=session_id,
            message=request.message,
        ):
            yield encode_sse(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
