"""当前用户档案解析、确认与读取接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from gopher_agent.api.dependencies.auth import get_current_user, get_user_repository
from gopher_agent.api.dependencies.profile import get_profile_service
from gopher_agent.api.schemas.profile import (
    AdvancedParseRequest,
    ConfirmProfileRequest,
    ConfirmProfileResponse,
    ParseRequest,
    ParseResponse,
    ProfileResponse,
)
from gopher_agent.domain.enums import UserMode
from gopher_agent.domain.profile import ProfileData
from gopher_agent.models.user import User
from gopher_agent.repositories.protocols import UserRepositoryProtocol
from gopher_agent.services.exceptions import (
    ProfileParserUnavailableError,
    ProfileParsingError,
    ProfileSessionConflictError,
    ProfileSessionNotFoundError,
)
from gopher_agent.services.profile import ProfileService

router = APIRouter(tags=["profile"])


@router.post("/parse", response_model=ParseResponse)
async def parse_profile(
    payload: ParseRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ParseResponse:
    """从自然语言或结构化输入创建待确认档案。"""
    try:
        result = await service.parse(
            user_id=current_user.id,
            mode=UserMode(payload.mode),
            content=None if isinstance(payload, AdvancedParseRequest) else payload.content,
            profile=payload.profile if isinstance(payload, AdvancedParseRequest) else None,
        )
    except ProfileParserUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="档案解析服务尚未启用或配置不完整",
        ) from error
    except ProfileParsingError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="档案解析失败",
        ) from error

    return ParseResponse(
        session_id=result.session_id,
        status=result.status,
        profile=result.profile,
        missing_fields=list(result.missing_fields),
        warnings=list(result.warnings),
    )


@router.post("/parse/confirm", response_model=ConfirmProfileResponse)
async def confirm_profile(
    payload: ConfirmProfileRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ConfirmProfileResponse:
    """确认或修正草稿，并原子更新当前用户权威档案。"""
    try:
        result = await service.confirm(
            user_id=current_user.id,
            session_id=payload.session_id,
            profile=payload.profile,
        )
    except ProfileSessionNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="档案解析会话不存在",
        ) from error
    except ProfileSessionConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="档案解析会话状态冲突",
        ) from error

    return ConfirmProfileResponse(
        session_id=result.session_id,
        status=result.status,
        profile=result.profile,
    )


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    users: Annotated[UserRepositoryProtocol, Depends(get_user_repository)],
) -> ProfileResponse:
    """返回当前用户强类型权威档案；尚未创建时各字段均为 null。"""
    profile = await users.get_profile_by_user_id(current_user.id)
    profile_data = ProfileData.model_validate(profile.profile if profile is not None else {})
    return ProfileResponse(user_id=current_user.id, profile=profile_data)
