"""认证相关 FastAPI dependencies。"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from gopher_agent.core.config import Settings, get_settings
from gopher_agent.core.database import get_session
from gopher_agent.core.security import PasswordHasher, TokenManager, TokenValidationError
from gopher_agent.models.user import User
from gopher_agent.repositories.protocols import UserRepositoryProtocol
from gopher_agent.repositories.sqlalchemy.user import SqlAlchemyUserRepository
from gopher_agent.services.auth import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_password_hasher() -> PasswordHasher:
    """复用初始化成本较高的 Argon2 helper 和 dummy hash。"""
    return PasswordHasher()


def get_token_manager(settings: Annotated[Settings, Depends(get_settings)]) -> TokenManager:
    """从强类型配置创建 token manager。"""
    return TokenManager(
        secret=settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.jwt_access_token_expire_minutes,
    )


def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserRepositoryProtocol:
    """为当前请求创建共享同一 session 的用户 Repository。"""
    return SqlAlchemyUserRepository(session)


def get_auth_service(
    users: Annotated[UserRepositoryProtocol, Depends(get_user_repository)],
    password_hasher: Annotated[PasswordHasher, Depends(get_password_hasher)],
    token_manager: Annotated[TokenManager, Depends(get_token_manager)],
) -> AuthService:
    """组装认证 Application Service。"""
    return AuthService(users, password_hasher, token_manager)


def credentials_error() -> HTTPException:
    """返回不泄露具体失败原因的统一认证错误。"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证身份凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    users: Annotated[UserRepositoryProtocol, Depends(get_user_repository)],
    token_manager: Annotated[TokenManager, Depends(get_token_manager)],
) -> User:
    """从 Bearer token 解析并加载当前用户。"""
    if credentials is None:
        raise credentials_error()
    try:
        user_id = token_manager.decode_user_id(credentials.credentials)
    except TokenValidationError as error:
        raise credentials_error() from error

    user = await users.get_by_id(user_id)
    if user is None:
        raise credentials_error()
    return user
