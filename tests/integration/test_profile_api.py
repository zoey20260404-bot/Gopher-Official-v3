"""用户档案解析与确认 HTTP 契约测试。"""

# ruff: noqa: S106 测试 hash 不是可用凭据。

from uuid import UUID

from fastapi.testclient import TestClient

from gopher_agent.api.dependencies.auth import get_current_user
from gopher_agent.api.dependencies.profile import get_profile_service
from gopher_agent.domain.enums import SessionStatus, UserMode
from gopher_agent.domain.profile import ProfileData
from gopher_agent.main import create_app
from gopher_agent.models.user import User
from gopher_agent.services.exceptions import (
    ProfileParserUnavailableError,
    ProfileParsingError,
    ProfileSessionConflictError,
    ProfileSessionNotFoundError,
)
from gopher_agent.services.profile import ProfileConfirmationResult, ProfileParseResult

SESSION_ID = UUID("0199d418-9f9a-7000-8000-000000000001")


def build_user() -> User:
    user = User(username="zoey", password_hash="hidden-hash")
    user.id = 7
    return user


class StubProfileService:
    """记录 route 参数并按需抛出领域错误。"""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.parse_args: tuple[int, UserMode, str | None, ProfileData | None] | None = None
        self.confirm_args: tuple[int, UUID, ProfileData] | None = None

    async def parse(
        self,
        *,
        user_id: int,
        mode: UserMode,
        content: str | None = None,
        profile: ProfileData | None = None,
    ) -> ProfileParseResult:
        if self.error is not None:
            raise self.error
        self.parse_args = (user_id, mode, content, profile)
        draft = profile or ProfileData(education="本科")
        return ProfileParseResult(
            session_id=SESSION_ID,
            status=SessionStatus.CONFIRMING,
            profile=draft,
            missing_fields=tuple(draft.missing_fields),
        )

    async def confirm(
        self,
        *,
        user_id: int,
        session_id: UUID,
        profile: ProfileData,
    ) -> ProfileConfirmationResult:
        if self.error is not None:
            raise self.error
        self.confirm_args = (user_id, session_id, profile)
        return ProfileConfirmationResult(
            session_id=session_id,
            status=SessionStatus.COMPLETED,
            profile=profile,
        )


def client_for(service: StubProfileService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = build_user
    app.dependency_overrides[get_profile_service] = lambda: service
    return TestClient(app)


def test_advanced_parse_returns_normalized_confirming_profile() -> None:
    service = StubProfileService()

    with client_for(service) as client:
        response = client.post(
            "/api/v1/parse",
            json={
                "mode": "advanced",
                "profile": {"education": "  本科  ", "age": 24},
            },
        )

    assert response.status_code == 200
    assert response.json()["session_id"] == str(SESSION_ID)
    assert response.json()["status"] == "confirming"
    assert response.json()["profile"]["education"] == "本科"
    assert "major" in response.json()["missing_fields"]
    assert service.parse_args is not None
    assert service.parse_args[:3] == (7, UserMode.ADVANCED, None)


def test_beginner_parse_maps_unavailable_and_provider_failures() -> None:
    with client_for(StubProfileService(ProfileParserUnavailableError())) as client:
        unavailable = client.post("/api/v1/parse", json={"mode": "beginner", "content": "本科"})
    with client_for(StubProfileService(ProfileParsingError())) as client:
        failed = client.post("/api/v1/parse", json={"mode": "beginner", "content": "本科"})

    assert unavailable.status_code == 503
    assert unavailable.json() == {"detail": "档案解析服务尚未启用或配置不完整"}
    assert failed.status_code == 502
    assert failed.json() == {"detail": "档案解析失败"}


def test_parse_schema_rejects_cross_mode_and_invalid_profile() -> None:
    service = StubProfileService()

    with client_for(service) as client:
        cross_mode = client.post(
            "/api/v1/parse",
            json={"mode": "beginner", "content": "本科", "profile": {}},
        )
        invalid_age = client.post(
            "/api/v1/parse",
            json={"mode": "advanced", "profile": {"age": 10}},
        )

    assert cross_mode.status_code == 422
    assert invalid_age.status_code == 422


def test_confirm_returns_completed_profile_and_maps_session_errors() -> None:
    service = StubProfileService()
    payload = {"session_id": str(SESSION_ID), "profile": {"major": "计算机"}}

    with client_for(service) as client:
        success = client.post("/api/v1/parse/confirm", json=payload)
    with client_for(StubProfileService(ProfileSessionNotFoundError())) as client:
        missing = client.post("/api/v1/parse/confirm", json=payload)
    with client_for(StubProfileService(ProfileSessionConflictError())) as client:
        conflict = client.post("/api/v1/parse/confirm", json=payload)

    assert success.status_code == 200
    assert success.json()["status"] == "completed"
    assert success.json()["profile"]["major"] == "计算机"
    assert service.confirm_args == (7, SESSION_ID, ProfileData(major="计算机"))
    assert missing.status_code == 404
    assert conflict.status_code == 409


def test_profile_endpoints_declare_bearer_security() -> None:
    paths = create_app().openapi()["paths"]

    assert paths["/api/v1/parse"]["post"]["security"] == [{"HTTPBearer": []}]
    assert paths["/api/v1/parse/confirm"]["post"]["security"] == [{"HTTPBearer": []}]
