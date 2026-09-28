"""选岗报告 API schemas。"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from gopher_agent.domain.enums import ReportStatus
from gopher_agent.domain.report import (
    GeneratedReport,
    PositionCode,
    ReportApproval,
    ReportProposal,
)


class CreateReportRequest(BaseModel):
    """创建选岗报告的候选过滤条件。"""

    model_config = ConfigDict(extra="forbid")

    exam_type: str | None = Field(default=None, max_length=20)
    year: int | None = Field(default=None, ge=2000, le=2100)
    province: str | None = Field(default=None, max_length=50)
    city: str | None = Field(default=None, max_length=100)
    keyword: str | None = Field(default=None, max_length=100)
    max_candidates: int = Field(default=10, ge=1, le=20)

    @field_validator("exam_type", "province", "city", "keyword", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        """把空白过滤条件统一为未提供。"""
        if not isinstance(value, str):
            return value
        return value.strip() or None


class DecideReportRequest(BaseModel):
    """批准或拒绝 interrupt 中的候选方案。"""

    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    decision: Literal["approve", "reject"]
    approved_position_codes: list[PositionCode] = Field(default_factory=list, max_length=20)

    @field_validator("approved_position_codes")
    @classmethod
    def normalize_codes(cls, values: list[str]) -> list[str]:
        """规范化岗位代码并拒绝空值。"""
        normalized = [value.strip() for value in values]
        if any(not value for value in normalized):
            raise ValueError("岗位代码不能为空")
        return normalized

    @model_validator(mode="after")
    def validate_decision(self) -> "DecideReportRequest":
        """批准必须选择岗位，拒绝不能携带岗位。"""
        if self.decision == "approve" and not self.approved_position_codes:
            raise ValueError("批准时必须选择至少一个岗位")
        if self.decision == "reject" and self.approved_position_codes:
            raise ValueError("拒绝时不能选择岗位")
        return self

    def to_domain(self) -> ReportApproval:
        """转换为 transport 无关的审批对象。"""
        return ReportApproval(
            decision=self.decision,
            approved_position_codes=self.approved_position_codes,
        )


class ReportResponse(BaseModel):
    """报告当前状态、审批方案和最终内容。"""

    report_id: UUID
    status: ReportStatus
    proposal: ReportProposal | None
    approval: ReportApproval | None
    generated_report: GeneratedReport | None
    content: str
