"""密码哈希与 JWT 单元测试。"""

# ruff: noqa: S105 测试数据不是可用凭据。

from datetime import UTC, datetime

import pytest

from gopher_agent.core.security import PasswordHasher, TokenManager, TokenValidationError

TEST_SECRET = "unit-test-secret-that-is-long-enough-123456"


def test_password_hasher_never_stores_plaintext_and_verifies() -> None:
    hasher = PasswordHasher()

    password_hash = hasher.hash("correct-password")

    assert password_hash != "correct-password"
    assert hasher.verify("correct-password", password_hash) is True
    assert hasher.verify("wrong-password", password_hash) is False


def test_token_manager_round_trips_user_id() -> None:
    manager = TokenManager(TEST_SECRET, "HS256", 60)

    token = manager.create_access_token(42)

    assert manager.decode_user_id(token) == 42
    assert manager.expires_in_seconds == 3600


def test_token_manager_rejects_expired_token() -> None:
    manager = TokenManager(TEST_SECRET, "HS256", 1)
    token = manager.create_access_token(42, now=datetime(2020, 1, 1, tzinfo=UTC))

    with pytest.raises(TokenValidationError):
        manager.decode_user_id(token)


@pytest.mark.parametrize(
    ("secret", "algorithm"),
    [("short", "HS256"), (TEST_SECRET, "none")],
)
def test_token_manager_rejects_unsafe_configuration(secret: str, algorithm: str) -> None:
    with pytest.raises(ValueError):
        TokenManager(secret, algorithm, 60)
