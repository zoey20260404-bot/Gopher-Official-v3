"""认证接口请求与响应 schema。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class CredentialsRequest(BaseModel):
    """注册和登录共用的规范化凭据。"""

    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_]+$")
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        """用户名统一去除首尾空白并转为小写。"""
        return value.strip().lower() if isinstance(value, str) else value


class RegisterRequest(CredentialsRequest):
    """注册请求。"""


class LoginRequest(CredentialsRequest):
    """登录请求。"""


class UserResponse(BaseModel):
    """可安全公开的用户信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class TokenResponse(BaseModel):
    """Bearer access token 响应。"""

    access_token: str
    token_type: str = "bearer"  # noqa: S105 OAuth2 token 类型，不是凭据
    expires_in: int
