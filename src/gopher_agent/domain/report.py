"""选岗报告 workflow 的稳定领域类型。"""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from gopher_agent.domain.matching import PositionMatchStatus, ReasonValue, RuleResult

PositionCode = Annotated[str, Field(min_length=1, max_length=100)]
ActionItem = Annotated[str, Field(min_length=1, max_length=300)]


class ReportDecision(StrEnum):
    """人工审批决策。"""

    APPROVE = "approve"
    REJECT = "reject"


class ReportReason(BaseModel):
    """候选岗位的一条确定性资格依据。"""

    model_config = ConfigDict(extra="forbid")

    field: str
    result: RuleResult
    code: str
    message: str
    profile_value: ReasonValue
    requirement: ReasonValue


class ReportCandidate(BaseModel):
    """提交人工审批的精简岗位事实。"""

    model_config = ConfigDict(extra="forbid")

    position_code: PositionCode
    position_name: str
    department: str
    exam_type: str
    year: int
    province: str
    city: str
    match_status: PositionMatchStatus
    missing_profile_fields: list[str] = Field(default_factory=list)
    reasons: list[ReportReason] = Field(default_factory=list)
    score_latest: int | None = None
    score_year: int | None = None
    applicant_ratio_2025: str = ""


class ReportProposal(BaseModel):
    """在 interrupt 中展示给用户的候选方案。"""

    model_config = ConfigDict(extra="forbid")

    candidates: list[ReportCandidate] = Field(min_length=1, max_length=20)


class ReportApproval(BaseModel):
    """恢复 graph 时注入的可信审批数据。"""

    model_config = ConfigDict(extra="forbid")

    decision: ReportDecision
    approved_position_codes: list[PositionCode] = Field(default_factory=list, max_length=20)


class GeneratedPositionAdvice(BaseModel):
    """LLM 针对一个已批准岗位生成的建议。"""

    model_config = ConfigDict(extra="forbid")

    position_code: PositionCode
    summary: str = Field(min_length=1, max_length=500)
    action_items: list[ActionItem] = Field(min_length=1, max_length=5)


class GeneratedReport(BaseModel):
    """LLM 生成且待 Service 复核的结构化报告。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    overview: str = Field(min_length=1, max_length=1000)
    positions: list[GeneratedPositionAdvice] = Field(min_length=1, max_length=20)
