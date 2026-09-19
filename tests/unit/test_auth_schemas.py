"""认证 Pydantic schema 单元测试。"""

# ruff: noqa: S106 测试数据不是可用凭据。

import pytest
from pydantic import ValidationError

from gopher_agent.api.schemas.auth import RegisterRequest


def test_credentials_normalize_username_and_hide_password() -> None:
    request = RegisterRequest(username="  Zoey_01  ", password="strong-password")

    assert request.username == "zoey_01"
    assert request.password.get_secret_value() == "strong-password"
    assert "strong-password" not in repr(request)


@pytest.mark.parametrize("username", ["ab", "zoey name", "中文用户", "zoey!"])
def test_credentials_reject_invalid_username(username: str) -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(username=username, password="strong-password")


def test_credentials_reject_short_password() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(username="zoey", password="short")
