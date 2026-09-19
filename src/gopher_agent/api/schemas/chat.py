"""Agent 对话 API schema。"""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """单轮对话输入；session ID 缺失时由服务端创建。"""

    message: str = Field(min_length=1, max_length=4000)
    session_id: UUID | None = None

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, value: object) -> object:
        """拒绝只有空白字符的消息。"""
        return value.strip() if isinstance(value, str) else value
