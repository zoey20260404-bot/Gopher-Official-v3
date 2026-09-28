"""用户档案 API schemas。"""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from gopher_agent.domain.enums import SessionStatus
from gopher_agent.domain.profile import ProfileData


class BeginnerParseRequest(BaseModel):
    """由自然语言提取档案的入门模式请求。"""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["beginner"]
    content: str = Field(min_length=1, max_length=8000)

    @field_validator("content", mode="before")
    @classmethod
    def strip_content(cls, value: object) -> object:
        """拒绝仅包含空白字符的自然语言输入。"""
        return value.strip() if isinstance(value, str) else value


class AdvancedParseRequest(BaseModel):
    """直接提交结构化档案的高级模式请求。"""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["advanced"]
    profile: ProfileData


ParseRequest = Annotated[
    BeginnerParseRequest | AdvancedParseRequest,
    Field(discriminator="mode"),
]


class ParseResponse(BaseModel):
    """等待用户检查和确认的档案草稿。"""

    session_id: UUID
    status: SessionStatus
    profile: ProfileData
    missing_fields: list[str]
    warnings: list[str]


class ConfirmProfileRequest(BaseModel):
    """用户修正并确认档案的请求。"""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    profile: ProfileData


class ConfirmProfileResponse(BaseModel):
    """确认成功后的权威档案。"""

    session_id: UUID
    status: SessionStatus
    profile: ProfileData


class ProfileResponse(BaseModel):
    """当前认证用户的权威档案响应。"""

    user_id: int
    profile: ProfileData
