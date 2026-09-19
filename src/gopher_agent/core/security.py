"""密码哈希与 JWT access token 基础能力。"""

from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash


class TokenValidationError(Exception):
    """Token 无法验证或不包含合法用户身份。"""


class PasswordHasher:
    """使用当前推荐的 Argon2 参数哈希和验证密码。"""

    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()
        # 用户不存在时仍执行一次 Argon2，降低用户名枚举的计时差异。
        self.dummy_hash = self._password_hash.hash("gopher-agent-dummy-password")

    def hash(self, password: str) -> str:
        """生成不可逆密码哈希。"""
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        """使用恒定接口验证密码。"""
        return self._password_hash.verify(password, password_hash)


class TokenManager:
    """签发并验证只承载用户标识的 JWT access token。"""

    def __init__(self, secret: str, algorithm: str, expire_minutes: int) -> None:
        if len(secret) < 32:
            raise ValueError("JWT_SECRET 必须至少包含 32 个字符")
        if algorithm != "HS256":
            raise ValueError("当前仅允许固定的 HS256 JWT 算法")
        self._secret = secret
        self._algorithm = algorithm
        self._expire_minutes = expire_minutes

    @property
    def expires_in_seconds(self) -> int:
        """返回 access token 生命周期秒数。"""
        return self._expire_minutes * 60

    def create_access_token(self, user_id: int, now: datetime | None = None) -> str:
        """为用户签发带 iat/exp 的 token。"""
        issued_at = now or datetime.now(UTC)
        expires_at = issued_at + timedelta(minutes=self._expire_minutes)
        return jwt.encode(
            {"sub": str(user_id), "iat": issued_at, "exp": expires_at},
            self._secret,
            algorithm=self._algorithm,
        )

    def decode_user_id(self, token: str) -> int:
        """验证 token 并返回正整数用户 ID。"""
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": ["sub", "iat", "exp"]},
            )
            user_id = int(payload["sub"])
            if user_id <= 0:
                raise ValueError
            return user_id
        except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
            raise TokenValidationError from error
