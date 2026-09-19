"""配置模型单元测试。"""

import pytest
from pydantic import ValidationError

from gopher_agent.core.config import Settings


def test_settings_has_safe_local_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "Gopher Agent"
    assert settings.app_debug is False
    assert settings.jwt_secret.get_secret_value() == ""
    assert settings.jwt_access_token_expire_minutes == 60


def test_settings_rejects_invalid_port() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_port=70_000)
