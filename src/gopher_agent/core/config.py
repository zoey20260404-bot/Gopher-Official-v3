"""集中式、强类型应用配置。"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从环境变量和本地 .env 文件读取配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Gopher Agent"
    app_env: str = "local"
    app_debug: bool = False
    app_host: str = "0.0.0.0"  # noqa: S104 本地容器需要对宿主机暴露服务
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://gopher:gopher@localhost:5432/gopher_agent"
    redis_url: str = "redis://localhost:6379/0"

    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""


@lru_cache
def get_settings() -> Settings:
    """缓存不可变来源的配置，避免每次依赖注入重复解析。"""
    return Settings()
