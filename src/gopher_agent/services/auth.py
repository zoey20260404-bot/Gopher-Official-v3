"""注册与登录 Application Service。"""

import asyncio

from gopher_agent.core.security import PasswordHasher, TokenManager
from gopher_agent.models.user import User
from gopher_agent.repositories.protocols import UserRepositoryProtocol
from gopher_agent.services.exceptions import (
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
)


class AuthService:
    """编排用户 Repository、密码哈希和 token 签发。"""

    def __init__(
        self,
        users: UserRepositoryProtocol,
        password_hasher: PasswordHasher,
        token_manager: TokenManager,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher
        self._token_manager = token_manager

    async def register(self, username: str, password: str) -> User:
        """注册用户；数据库唯一约束仍是并发冲突的最终防线。"""
        if await self._users.get_by_username(username) is not None:
            raise UsernameAlreadyExistsError

        # Argon2 是 CPU 密集操作，放入工作线程避免阻塞 asyncio event loop。
        password_hash = await asyncio.to_thread(self._password_hasher.hash, password)
        return await self._users.add(User(username=username, password_hash=password_hash))

    async def login(self, username: str, password: str) -> tuple[str, int]:
        """校验凭据并返回 access token 和有效期。"""
        user = await self._users.get_by_username(username)
        candidate_hash = (
            user.password_hash if user is not None else self._password_hasher.dummy_hash
        )
        password_valid = await asyncio.to_thread(
            self._password_hasher.verify,
            password,
            candidate_hash,
        )
        if user is None or not password_valid:
            raise InvalidCredentialsError

        return (
            self._token_manager.create_access_token(user.id),
            self._token_manager.expires_in_seconds,
        )
