"""档案 Interview HTTP 契约测试。"""

# ruff: noqa: S106 测试 hash 不是可用凭据。

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from gopher_agent.api.dependencies.auth import get_current_user
from gopher_agent.api.dependencies.profile import get_profile_interview_service
from gopher_agent.domain.interview import InterviewField, InterviewStatus
from gopher_agent.domain.profile import ProfileData
from gopher_agent.main import create_app
from gopher_agent.models.user import User
from gopher_agent.services.exceptions import (
    ProfileInterviewConflictError,
    ProfileParserUnavailableError,
    ProfileParsingError,
    ProfileSessionNotFoundError,
)
from gopher_agent.services.interview import ProfileInterviewResult

SESSION_ID = UUID("0199d418-9f9a-7000-8000-000000000001")
QUESTION_ID = UUID("0199d418-9f9a-7000-8000-000000000002")
REQUEST_ID = UUID("0199d418-9f9a-7000-8000-000000000003")


def build_user() -> User:
    user = User(username="zoey", password_hash="hidden-hash")
    user.id = 7
    return user


class StubInterviewService:
    """记录 route 参数并返回固定访谈视图。"""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.start_args: tuple[int, UUID | None] | None = None
        self.answer_args: tuple[int, UUID, UUID, UUID, str | None, bool] | None = None

    async def start(
        self, *, user_id: int, session_id: UUID | None = None
    ) -> ProfileInterviewResult:
        if self.error is not None:
            raise self.error
        self.start_args = (user_id, session_id)
        return self._result()

    async def answer(
        self,
        *,
        user_id: int,
        session_id: UUID,
        question_id: UUID,
        request_id: UUID,
        answer: str | None,
        skip: bool,
    ) -> ProfileInterviewResult:
        if self.error is not None:
            raise self.error
        self.answer_args = (user_id, session_id, question_id, request_id, answer, skip)
        return self._result()

    @staticmethod
    def _result() -> ProfileInterviewResult:
        return ProfileInterviewResult(
            session_id=SESSION_ID,
            interview_status=InterviewStatus.WAITING_ANSWER,
            question_id=QUESTION_ID,
            current_field=InterviewField.EDUCATION,
            question="你的最高学历是什么？",  # noqa: RUF001 API 返回自然语言中文标点
            profile=ProfileData(),
            missing_fields=tuple(InterviewField),
            skipped_fields=(),
        )


def client_for(service: StubInterviewService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = build_user
    app.dependency_overrides[get_profile_interview_service] = lambda: service
    return TestClient(app)


def test_start_and_answer_return_stable_interview_contract() -> None:
    service = StubInterviewService()
    answer_payload = {
        "session_id": str(SESSION_ID),
        "question_id": str(QUESTION_ID),
        "request_id": str(REQUEST_ID),
        "answer": "  本科  ",
    }

    with client_for(service) as client:
        started = client.post("/api/v1/parse/interview/start", json={})
        answered = client.post("/api/v1/parse/interview/answer", json=answer_payload)

    assert started.status_code == 200
    assert started.json()["interview_status"] == "waiting_answer"
    assert started.json()["current_field"] == "education"
    assert started.json()["question_id"] == str(QUESTION_ID)
    assert service.start_args == (7, None)
    assert answered.status_code == 200
    assert service.answer_args == (
        7,
        SESSION_ID,
        QUESTION_ID,
        REQUEST_ID,
        "本科",
        False,
    )


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (ProfileSessionNotFoundError(), 404),
        (ProfileInterviewConflictError(), 409),
        (ProfileParserUnavailableError(), 503),
        (ProfileParsingError(), 502),
    ],
)
def test_answer_maps_domain_errors(error: Exception, expected_status: int) -> None:
    payload = {
        "session_id": str(SESSION_ID),
        "question_id": str(QUESTION_ID),
        "request_id": str(REQUEST_ID),
        "answer": "本科",
    }

    with client_for(StubInterviewService(error)) as client:
        response = client.post("/api/v1/parse/interview/answer", json=payload)

    assert response.status_code == expected_status


def test_answer_schema_rejects_ambiguous_or_blank_input() -> None:
    base = {
        "session_id": str(SESSION_ID),
        "question_id": str(QUESTION_ID),
        "request_id": str(REQUEST_ID),
    }

    with client_for(StubInterviewService()) as client:
        missing = client.post("/api/v1/parse/interview/answer", json=base)
        ambiguous = client.post(
            "/api/v1/parse/interview/answer",
            json={**base, "answer": "本科", "skip": True},
        )
        blank = client.post("/api/v1/parse/interview/answer", json={**base, "answer": "   "})

    assert missing.status_code == 422
    assert ambiguous.status_code == 422
    assert blank.status_code == 422


def test_interview_endpoints_declare_bearer_security() -> None:
    paths = create_app().openapi()["paths"]

    assert paths["/api/v1/parse/interview/start"]["post"]["security"] == [{"HTTPBearer": []}]
    assert paths["/api/v1/parse/interview/answer"]["post"]["security"] == [{"HTTPBearer": []}]
