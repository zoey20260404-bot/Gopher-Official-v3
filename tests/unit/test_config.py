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
    assert settings.agent_enabled is False
    assert settings.llm_api_key.get_secret_value() == ""
    assert settings.agent_max_iterations == 8
    assert settings.checkpoint_ttl_minutes == 1440
    assert settings.position_match_candidate_limit == 2000


def test_settings_rejects_invalid_port() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_port=70_000)


@pytest.mark.parametrize("limit", [99, 10_001])
def test_settings_rejects_unsafe_position_candidate_limit(limit: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, position_match_candidate_limit=limit)
