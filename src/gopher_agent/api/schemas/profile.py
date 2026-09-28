"""用户档案 API schemas。"""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from gopher_agent.domain.enums import SessionStatus
from gopher_agent.domain.interview import InterviewField, InterviewStatus
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


class StartProfileInterviewRequest(BaseModel):
    """开始新访谈或继续已有待确认 session。"""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID | None = None


class AnswerProfileInterviewRequest(BaseModel):
    """回答或显式跳过当前访谈问题。"""

    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    question_id: UUID
    request_id: UUID
    answer: str | None = Field(default=None, min_length=1, max_length=1000)
    skip: bool = False

    @field_validator("answer", mode="before")
    @classmethod
    def strip_answer(cls, value: object) -> object:
        """去除回答首尾空白，并让空白回答进入长度校验。"""
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_answer_mode(self) -> "AnswerProfileInterviewRequest":
        """跳过与自然语言回答必须互斥。"""
        if self.skip and self.answer is not None:
            raise ValueError("skip=true 时不能同时提供 answer")
        if not self.skip and self.answer is None:
            raise ValueError("skip=false 时必须提供 answer")
        return self


class ProfileInterviewResponse(BaseModel):
    """当前访谈问题、档案快照和补全进度。"""

    session_id: UUID
    interview_status: InterviewStatus
    question_id: UUID | None
    current_field: InterviewField | None
    question: str | None
    profile: ProfileData
    missing_fields: list[InterviewField]
    skipped_fields: list[InterviewField]
