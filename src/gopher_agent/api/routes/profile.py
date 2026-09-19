"""当前用户档案接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from gopher_agent.api.dependencies.auth import get_current_user, get_user_repository
from gopher_agent.api.schemas.profile import ProfileResponse
from gopher_agent.models.user import User
from gopher_agent.repositories.protocols import UserRepositoryProtocol

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    users: Annotated[UserRepositoryProtocol, Depends(get_user_repository)],
) -> ProfileResponse:
    """返回当前用户权威档案；尚未创建时返回空对象。"""
    profile = await users.get_profile_by_user_id(current_user.id)
    return ProfileResponse(
        user_id=current_user.id,
        profile=profile.profile if profile is not None else {},
    )
