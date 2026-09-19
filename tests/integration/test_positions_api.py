"""岗位查询 HTTP 契约测试。"""

# ruff: noqa: S105, S106 测试 secret 和 hash 不是可用凭据。

from typing import Any

from fastapi.testclient import TestClient

from gopher_agent.api.dependencies.auth import (
    get_current_user,
    get_token_manager,
    get_user_repository,
)
from gopher_agent.api.dependencies.positions import get_position_search_service
from gopher_agent.core.security import TokenManager
from gopher_agent.main import create_app
from gopher_agent.models.user import User, UserProfile
from gopher_agent.repositories.types import PositionQuery
from gopher_agent.services.positions import (
    PositionItem,
    PositionSearchResult,
    PositionSearchService,
)

TEST_SECRET = "position-api-secret-that-is-long-enough-123"


def build_user() -> User:
    user = User(username="zoey", password_hash="hidden-hash")
    user.id = 7
    return user


def build_item() -> PositionItem:
    return PositionItem(
        id=11,
        exam_type="国考",
        year=2026,
        province="广东",
        city="广州",
        department="税务局",
        position_name="一级行政执法员",
        position_code="001",
        education_req="本科及以上",
        major_req_exact="计算机科学与技术",
        major_req_category="计算机类",
        political_req="不限",
        fresh_graduate_req=True,
        work_experience_years_req=0,
        gender_req="不限",
        age_limit=35,
        household_registration_req="",
        other_restrictions=[],
        remarks="",
        score_2025=135,
        score_2024=None,
        score_latest=135,
        score_year=2025,
        applicant_ratio_2025="120:1",
    )


class StubPositionSearchService(PositionSearchService):
    """绕过数据库并记录 route 生成的查询。"""

    def __init__(self, *, empty: bool = False) -> None:
        self.query: PositionQuery | None = None
        self.empty = empty

    async def search(self, query: PositionQuery) -> PositionSearchResult:
        self.query = query
        items = [] if self.empty else [build_item()]
        return PositionSearchResult(
            items=items, total=len(items), page=query.page, page_size=query.page_size
        )


class StubUserRepository:
    async def add(self, user: User) -> User:
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        return None

    async def get_by_username(self, username: str) -> User | None:
        return None

    async def get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        return None


def test_positions_returns_authenticated_filtered_page_without_internal_fields() -> None:
    app = create_app()
    service = StubPositionSearchService()
    app.dependency_overrides[get_current_user] = build_user
    app.dependency_overrides[get_position_search_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/positions",
            params={"exam_type": " 国考 ", "province": "广东", "page": 2, "page_size": 10},
        )

    assert response.status_code == 200
    assert service.query == PositionQuery(exam_type="国考", province="广东", page=2, page_size=10)
    body = response.json()
    assert body["total"] == 1
    assert body["page"] == 2
    assert body["items"][0]["position_code"] == "001"
    assert "source_url" not in body["items"][0]
    assert "data_version" not in body["items"][0]


def test_positions_returns_empty_page_and_rejects_invalid_pagination() -> None:
    app = create_app()
    service = StubPositionSearchService(empty=True)
    app.dependency_overrides[get_current_user] = build_user
    app.dependency_overrides[get_position_search_service] = lambda: service

    with TestClient(app) as client:
        empty = client.get("/api/v1/positions")
        invalid = client.get("/api/v1/positions", params={"page_size": 101})

    assert empty.status_code == 200
    assert empty.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}
    assert invalid.status_code == 422


def test_positions_requires_bearer_credentials() -> None:
    app = create_app()
    app.dependency_overrides[get_user_repository] = lambda: StubUserRepository()
    app.dependency_overrides[get_token_manager] = lambda: TokenManager(TEST_SECRET, "HS256", 60)

    with TestClient(app) as client:
        response = client.get("/api/v1/positions")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_positions_openapi_exposes_query_response_and_bearer_security() -> None:
    schema: dict[str, Any] = create_app().openapi()
    operation = schema["paths"]["/api/v1/positions"]["get"]

    assert {parameter["name"] for parameter in operation["parameters"]} >= {
        "exam_type",
        "year",
        "province",
        "city",
        "keyword",
        "page",
        "page_size",
    }
    assert operation["security"] == [{"HTTPBearer": []}]
    item_properties = schema["components"]["schemas"]["PositionItemResponse"]["properties"]
    assert "source_url" not in item_properties
    assert "data_version" not in item_properties
