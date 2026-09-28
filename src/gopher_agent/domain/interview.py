"""多轮档案访谈的确定性领域状态。"""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class InterviewStatus(StrEnum):
    """档案访谈状态。"""

    WAITING_ANSWER = "waiting_answer"
    NEEDS_CLARIFICATION = "needs_clarification"
    READY_TO_CONFIRM = "ready_to_confirm"


class InterviewField(StrEnum):
    """访谈覆盖的岗位硬条件字段。"""

    EDUCATION = "education"
    MAJOR = "major"
    POLITICAL_STATUS = "political_status"
    FRESH_GRADUATE = "fresh_graduate"
    WORK_EXPERIENCE_YEARS = "work_experience_years"
    GENDER = "gender"
    AGE = "age"
    HOUSEHOLD_REGISTRATION = "household_registration"


INTERVIEW_FIELDS: tuple[InterviewField, ...] = tuple(InterviewField)

INTERVIEW_QUESTIONS: dict[InterviewField, str] = {
    InterviewField.EDUCATION: "你的最高学历是什么\uff1f",
    InterviewField.MAJOR: "你的专业是什么\uff1f",
    InterviewField.POLITICAL_STATUS: "你的政治面貌是什么\uff1f",
    InterviewField.FRESH_GRADUATE: "你是否属于应届毕业生\uff1f",
    InterviewField.WORK_EXPERIENCE_YEARS: "你有多少年工作经验\uff1f",
    InterviewField.GENDER: "你的性别是什么\uff1f",
    InterviewField.AGE: "你的年龄是多少\uff1f",
    InterviewField.HOUSEHOLD_REGISTRATION: "你的户籍所在地是哪里\uff1f",
}


class InterviewState(BaseModel):
    """持久化在 session 中的访谈状态。"""

    model_config = ConfigDict(extra="forbid")

    status: InterviewStatus
    current_field: InterviewField | None = None
    question_id: UUID | None = None
    asked_fields: list[InterviewField] = Field(default_factory=list)
    skipped_fields: list[InterviewField] = Field(default_factory=list)
    turn: int = Field(default=0, ge=0, le=len(INTERVIEW_FIELDS))
    last_request_id: UUID | None = None

    @model_validator(mode="after")
    def validate_state_invariants(self) -> "InterviewState":
        """拒绝无法由确定性状态机产生的持久化状态。"""
        ready = self.status is InterviewStatus.READY_TO_CONFIRM
        if ready != (self.current_field is None and self.question_id is None):
            raise ValueError("访谈状态与当前问题不一致")
        if len(set(self.asked_fields)) != len(self.asked_fields):
            raise ValueError("asked_fields 不能重复")
        if len(set(self.skipped_fields)) != len(self.skipped_fields):
            raise ValueError("skipped_fields 不能重复")
        if not set(self.skipped_fields).issubset(self.asked_fields):
            raise ValueError("跳过字段必须已经提问")
        if self.turn != len(self.asked_fields):
            raise ValueError("turn 必须等于已提问字段数")
        return self


class InterviewAnswerExtraction(BaseModel):
    """LLM 对单个当前字段的最小 structured output。"""

    model_config = ConfigDict(extra="forbid")

    understood: bool
    value: str | int | bool | None = None
