"""认证 Application Service 单元测试。"""

# ruff: noqa: S105, S106 测试数据不是可用凭据。

import pytest

from gopher_agent.core.security import PasswordHasher, TokenManager
from gopher_agent.models.user import User, UserProfile
from gopher_agent.services.auth import AuthService
from gopher_agent.services.exceptions import (
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
)

TEST_SECRET = "unit-test-secret-that-is-long-enough-123456"


class FakeUserRepository:
    """以内存字典隔离数据库，验证 Service 业务分支。"""

    def __init__(self) -> None:
        self.users: dict[str, User] = {}

    async def add(self, user: User) -> User:
        user.id = len(self.users) + 1
        self.users[user.username] = user
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        return next((user for user in self.users.values() if user.id == user_id), None)

    async def get_by_username(self, username: str) -> User | None:
        return self.users.get(username)

    async def get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        return None


def build_service(repository: FakeUserRepository) -> AuthService:
    return AuthService(
        repository,
        PasswordHasher(),
        TokenManager(TEST_SECRET, "HS256", 60),
    )


async def test_register_hashes_password_and_login_returns_token() -> None:
    repository = FakeUserRepository()
    service = build_service(repository)

    user = await service.register("zoey", "strong-password")
    token, expires_in = await service.login("zoey", "strong-password")

    assert user.username == "zoey"
    assert user.password_hash != "strong-password"
    assert expires_in == 3600
    assert TokenManager(TEST_SECRET, "HS256", 60).decode_user_id(token) == user.id


async def test_register_rejects_existing_username() -> None:
    repository = FakeUserRepository()
    existing = User(username="zoey", password_hash="existing-hash")
    existing.id = 1
    repository.users[existing.username] = existing

    with pytest.raises(UsernameAlreadyExistsError):
        await build_service(repository).register("zoey", "strong-password")


@pytest.mark.parametrize("username", ["missing", "zoey"])
async def test_login_uses_same_error_for_unknown_user_and_wrong_password(username: str) -> None:
    repository = FakeUserRepository()
    service = build_service(repository)
    await service.register("zoey", "correct-password")

    with pytest.raises(InvalidCredentialsError):
        await service.login(username, "wrong-password")
