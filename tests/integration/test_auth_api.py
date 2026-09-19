"""认证和当前档案 HTTP 契约测试。"""

# ruff: noqa: S105, S106 测试数据不是可用凭据。

from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from gopher_agent.api.dependencies.auth import (
    get_auth_service,
    get_current_user,
    get_user_repository,
)
from gopher_agent.core.database import get_session
from gopher_agent.main import create_app
from gopher_agent.models.user import User, UserProfile
from gopher_agent.services.exceptions import InvalidCredentialsError


class FakeSession:
    """记录 route 是否进入显式 transaction。"""

    entered = False

    def begin(self) -> "FakeSession":
        return self

    async def __aenter__(self) -> "FakeSession":
        self.entered = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> None:
        return None


class StubAuthService:
    def __init__(self) -> None:
        self.registered: tuple[str, str] | None = None

    async def register(self, username: str, password: str) -> User:
        self.registered = (username, password)
        user = User(username=username, password_hash="hidden-hash")
        user.id = 7
        user.created_at = datetime(2026, 9, 19, tzinfo=UTC)
        return user

    async def login(self, username: str, password: str) -> tuple[str, int]:
        if password != "strong-password":
            raise InvalidCredentialsError
        return "signed-token", 3600


class StubUserRepository:
    def __init__(self, profile: UserProfile | None = None) -> None:
        self.profile = profile

    async def add(self, user: User) -> User:
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        return None

    async def get_by_username(self, username: str) -> User | None:
        return None

    async def get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        return self.profile


def build_user() -> User:
    user = User(username="zoey", password_hash="hidden-hash")
    user.id = 7
    user.created_at = datetime(2026, 9, 19, tzinfo=UTC)
    return user


def test_register_normalizes_input_and_never_returns_password_hash() -> None:
    app = create_app()
    session = FakeSession()
    service = StubAuthService()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_auth_service] = lambda: service

    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={"username": "  Zoey  ", "password": "strong-password"},
        )

    assert response.status_code == 201
    assert response.json()["username"] == "zoey"
    assert "password_hash" not in response.json()
    assert service.registered == ("zoey", "strong-password")
    assert session.entered is True


def test_login_returns_token_and_hides_failure_reason() -> None:
    app = create_app()
    service = StubAuthService()
    app.dependency_overrides[get_auth_service] = lambda: service

    with TestClient(app) as client:
        success = client.post(
            "/auth/login",
            json={"username": "zoey", "password": "strong-password"},
        )
        failure = client.post(
            "/auth/login",
            json={"username": "zoey", "password": "wrong-password"},
        )

    assert success.status_code == 200
    assert success.json() == {
        "access_token": "signed-token",
        "token_type": "bearer",
        "expires_in": 3600,
    }
    assert failure.status_code == 401
    assert failure.json() == {"detail": "用户名或密码错误"}


def test_profile_uses_authenticated_user_and_returns_empty_default() -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = build_user
    app.dependency_overrides[get_user_repository] = lambda: StubUserRepository()

    with TestClient(app) as client:
        response = client.get("/api/v1/profile")

    assert response.status_code == 200
    assert response.json() == {"user_id": 7, "profile": {}}


def test_openapi_exposes_bearer_auth_without_password_hash_schema() -> None:
    schema: dict[str, Any] = create_app().openapi()

    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    user_response = schema["components"]["schemas"]["UserResponse"]
    assert "password_hash" not in user_response["properties"]
