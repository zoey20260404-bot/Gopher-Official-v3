"""认证 dependency 单元测试。"""

# ruff: noqa: S105 测试数据不是可用凭据。

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from gopher_agent.api.dependencies.auth import get_current_user
from gopher_agent.core.security import TokenManager
from gopher_agent.models.user import User

TEST_SECRET = "unit-test-secret-that-is-long-enough-123456"


class StubUserRepository:
    def __init__(self, user: User | None) -> None:
        self.user = user
        self.get_by_id = AsyncMock(return_value=user)


async def test_current_user_rejects_missing_bearer_token() -> None:
    repository = StubUserRepository(None)
    manager = TokenManager(TEST_SECRET, "HS256", 60)

    with pytest.raises(HTTPException) as captured:
        await get_current_user(None, repository, manager)  # type: ignore[arg-type]

    assert captured.value.status_code == 401
    repository.get_by_id.assert_not_awaited()


async def test_current_user_rejects_invalid_token() -> None:
    repository = StubUserRepository(None)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")

    with pytest.raises(HTTPException) as captured:
        await get_current_user(
            credentials,
            repository,  # type: ignore[arg-type]
            TokenManager(TEST_SECRET, "HS256", 60),
        )

    assert captured.value.status_code == 401
    assert captured.value.headers == {"WWW-Authenticate": "Bearer"}


async def test_current_user_loads_token_subject() -> None:
    user = User(username="zoey", password_hash="test-value")  # noqa: S106
    user.id = 42
    repository = StubUserRepository(user)
    manager = TokenManager(TEST_SECRET, "HS256", 60)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=manager.create_access_token(42),
    )

    result = await get_current_user(credentials, repository, manager)  # type: ignore[arg-type]

    assert result is user
    repository.get_by_id.assert_awaited_once_with(42)


async def test_current_user_rejects_deleted_user() -> None:
    repository = StubUserRepository(None)
    manager = TokenManager(TEST_SECRET, "HS256", 60)
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=manager.create_access_token(42),
    )

    with pytest.raises(HTTPException) as captured:
        await get_current_user(credentials, repository, manager)  # type: ignore[arg-type]

    assert captured.value.status_code == 401
