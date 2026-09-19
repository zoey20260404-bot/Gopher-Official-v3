"""岗位查询 HTTP 接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from gopher_agent.api.dependencies.auth import get_current_user
from gopher_agent.api.dependencies.positions import get_position_search_service
from gopher_agent.api.schemas.positions import PositionListResponse, PositionSearchParams
from gopher_agent.models.user import User
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
