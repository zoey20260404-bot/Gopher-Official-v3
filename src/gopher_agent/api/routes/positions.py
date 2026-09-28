"""岗位查询 HTTP 接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from gopher_agent.api.dependencies.auth import get_current_user
from gopher_agent.api.dependencies.positions import (
    get_position_match_service,
    get_position_search_service,
)
from gopher_agent.api.schemas.positions import (
    PositionListResponse,
    PositionMatchListResponse,
    PositionMatchParams,
    PositionSearchParams,
)
from gopher_agent.models.user import User
from gopher_agent.services.exceptions import (
    PositionCandidateLimitExceededError,
    UserProfileNotConfirmedError,
)
from gopher_agent.services.matching import PositionMatchService
from gopher_agent.services.positions import PositionSearchService

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=PositionListResponse)
async def list_positions(
    params: Annotated[PositionSearchParams, Depends()],
    _current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PositionSearchService, Depends(get_position_search_service)],
) -> PositionListResponse:
    """为已认证用户返回经过过滤的岗位分页结果。"""
    result = await service.search(params.to_query())
    return PositionListResponse.model_validate(result, from_attributes=True)


@router.get("/matches", response_model=PositionMatchListResponse)
async def match_positions(
    params: Annotated[PositionMatchParams, Depends()],
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[PositionMatchService, Depends(get_position_match_service)],
) -> PositionMatchListResponse:
    """基于当前用户权威档案返回可解释的三态岗位匹配。"""
    try:
        result = await service.search(current_user.id, params.to_match_query())
    except UserProfileNotConfirmedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="请先解析并确认用户档案",
        ) from error
    except PositionCandidateLimitExceededError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "position_candidate_limit_exceeded",
                "message": "候选岗位过多, 请增加考试、年份或地区过滤条件",
                "candidate_count": error.candidate_count,
                "limit": error.limit,
            },
        ) from error
    return PositionMatchListResponse.model_validate(result, from_attributes=True)
