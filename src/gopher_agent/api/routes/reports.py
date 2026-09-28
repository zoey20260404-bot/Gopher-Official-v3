"""选岗报告创建、审批与读取接口。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from gopher_agent.api.dependencies.auth import get_current_user
from gopher_agent.api.dependencies.reports import get_report_service
from gopher_agent.api.schemas.reports import (
    CreateReportRequest,
    DecideReportRequest,
    ReportResponse,
)
from gopher_agent.models.user import User
from gopher_agent.services.exceptions import (
    PositionCandidateLimitExceededError,
    ReportConflictError,
    ReportGenerationError,
    ReportNoCandidatesError,
    ReportNotFoundError,
    ReportWorkflowUnavailableError,
    UserProfileNotConfirmedError,
)
from gopher_agent.services.report import ReportCreateQuery, ReportService, ReportView

router = APIRouter(prefix="/reports", tags=["reports"])
REPORT_ROUTE_ERRORS = (
    PositionCandidateLimitExceededError,
    ReportConflictError,
    ReportGenerationError,
    ReportNoCandidatesError,
    ReportNotFoundError,
    ReportWorkflowUnavailableError,
    UserProfileNotConfirmedError,
)


def _response(view: ReportView) -> ReportResponse:
    """把 Application Service 视图转换为 HTTP response。"""
    return ReportResponse(
        report_id=view.report_id,
        status=view.status,
        proposal=view.proposal,
        approval=view.approval,
        generated_report=view.generated_report,
        content=view.content,
    )


def _raise_report_error(error: Exception) -> None:
    """集中映射报告 use case 的稳定 HTTP 错误。"""
    if isinstance(error, ReportNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在") from error
    if isinstance(error, (ReportConflictError, UserProfileNotConfirmedError)):
        detail = "报告状态或审批内容冲突"
        if isinstance(error, UserProfileNotConfirmedError):
            detail = "请先确认用户档案"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from error
    if isinstance(error, (ReportNoCandidatesError, PositionCandidateLimitExceededError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="当前条件下没有可生成报告的有界候选岗位",
        ) from error
    if isinstance(error, ReportWorkflowUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="报告生成服务尚未启用或配置不完整",
        ) from error
    if isinstance(error, ReportGenerationError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="报告生成失败",
        ) from error
    raise error


@router.post("", response_model=ReportResponse)
async def create_report(
    payload: CreateReportRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
) -> ReportResponse:
    """创建报告并运行至 LangGraph 人工审批暂停点。"""
    try:
        view = await service.create(
            user_id=current_user.id,
            query=ReportCreateQuery(**payload.model_dump()),
        )
    except REPORT_ROUTE_ERRORS as error:
        _raise_report_error(error)
        raise  # pragma: no cover - 映射函数总是抛出异常
    return _response(view)


@router.post("/{report_id}/decision", response_model=ReportResponse)
async def decide_report(
    report_id: UUID,
    payload: DecideReportRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
) -> ReportResponse:
    """提交人工审批并从 checkpoint 恢复报告 workflow。"""
    try:
        view = await service.decide(
            user_id=current_user.id,
            report_id=report_id,
            request_id=payload.request_id,
            approval=payload.to_domain(),
        )
    except REPORT_ROUTE_ERRORS as error:
        _raise_report_error(error)
        raise  # pragma: no cover
    return _response(view)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
) -> ReportResponse:
    """读取当前用户拥有的报告。"""
    try:
        view = await service.get(user_id=current_user.id, report_id=report_id)
    except REPORT_ROUTE_ERRORS as error:
        _raise_report_error(error)
        raise  # pragma: no cover
    return _response(view)
