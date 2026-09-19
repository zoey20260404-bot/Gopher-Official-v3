"""注册和登录 HTTP 接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from gopher_agent.api.dependencies.auth import get_auth_service
from gopher_agent.api.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from gopher_agent.core.database import get_session
from gopher_agent.services.auth import AuthService
from gopher_agent.services.exceptions import (
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """注册用户，整个写入由请求级显式 transaction 管理。"""
    try:
        async with session.begin():
            user = await service.register(request.username, request.password.get_secret_value())
    except UsernameAlreadyExistsError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在") from error
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """验证用户名和密码并签发 access token。"""
    try:
        access_token, expires_in = await service.login(
            request.username,
            request.password.get_secret_value(),
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    return TokenResponse(access_token=access_token, expires_in=expires_in)
