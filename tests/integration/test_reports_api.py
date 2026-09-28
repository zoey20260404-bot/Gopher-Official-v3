"""选岗报告 HTTP 契约测试。"""

# ruff: noqa: S106 测试 hash 不是可用凭据。

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from gopher_agent.api.dependencies.auth import get_current_user
from gopher_agent.api.dependencies.reports import get_report_service
from gopher_agent.domain.enums import ReportStatus
from gopher_agent.domain.report import (
    ReportApproval,
    ReportCandidate,
    ReportDecision,
    ReportProposal,
)
from gopher_agent.main import create_app
from gopher_agent.models.user import User
from gopher_agent.services.exceptions import (
    ReportConflictError,
    ReportGenerationError,
    ReportNotFoundError,
    ReportWorkflowUnavailableError,
)
from gopher_agent.services.report import ReportCreateQuery, ReportView

REPORT_ID = UUID("0199d418-9f9a-7000-8000-000000000011")
REQUEST_ID = UUID("0199d418-9f9a-7000-8000-000000000012")


def build_user() -> User:
    user = User(username="zoey", password_hash="hidden-hash")
    user.id = 7
    return user


def report_view(status: ReportStatus = ReportStatus.PENDING_APPROVAL) -> ReportView:
    proposal = ReportProposal(
        candidates=[
            ReportCandidate(
                position_code="P1",
                position_name="一级行政执法员",
                department="税务局",
                exam_type="国考",
                year=2026,
                province="广东",
                city="广州",
                match_status="eligible",
            )
        ]
    )
    return ReportView(
        report_id=REPORT_ID,
        status=status,
        proposal=proposal,
        approval=None,
        generated_report=None,
        content="",
    )


class StubReportService:
    """记录 route 参数并返回固定报告。"""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.create_args: tuple[int, ReportCreateQuery] | None = None
        self.decision_args: tuple[int, UUID, UUID, ReportApproval] | None = None
        self.get_args: tuple[int, UUID] | None = None

    async def create(self, *, user_id: int, query: ReportCreateQuery) -> ReportView:
        if self.error is not None:
            raise self.error
        self.create_args = (user_id, query)
        return report_view()

    async def decide(
        self,
        *,
        user_id: int,
        report_id: UUID,
        request_id: UUID,
        approval: ReportApproval,
    ) -> ReportView:
        if self.error is not None:
            raise self.error
        self.decision_args = (user_id, report_id, request_id, approval)
        return report_view(ReportStatus.COMPLETED)

    async def get(self, *, user_id: int, report_id: UUID) -> ReportView:
        if self.error is not None:
            raise self.error
        self.get_args = (user_id, report_id)
        return report_view()


def client_for(service: StubReportService) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_current_user] = build_user
    app.dependency_overrides[get_report_service] = lambda: service
    return TestClient(app)


def test_create_decide_and_get_report_contracts() -> None:
    service = StubReportService()
    with client_for(service) as client:
        created = client.post(
            "/api/v1/reports",
            json={"province": "  广东  ", "max_candidates": 5},
        )
        decided = client.post(
            f"/api/v1/reports/{REPORT_ID}/decision",
            json={
                "request_id": str(REQUEST_ID),
                "decision": "approve",
                "approved_position_codes": [" P1 "],
            },
        )
        fetched = client.get(f"/api/v1/reports/{REPORT_ID}")

    assert created.status_code == 200
    assert created.json()["status"] == "pending_approval"
    assert service.create_args == (7, ReportCreateQuery(province="广东", max_candidates=5))
    assert decided.status_code == 200
    assert service.decision_args == (
        7,
        REPORT_ID,
        REQUEST_ID,
        ReportApproval(
            decision=ReportDecision.APPROVE,
            approved_position_codes=["P1"],
        ),
    )
    assert fetched.status_code == 200
    assert service.get_args == (7, REPORT_ID)


def test_decision_schema_rejects_invalid_approval_shapes() -> None:
    base = {"request_id": str(REQUEST_ID)}
    with client_for(StubReportService()) as client:
        no_codes = client.post(
            f"/api/v1/reports/{REPORT_ID}/decision",
            json={**base, "decision": "approve"},
        )
        reject_with_codes = client.post(
            f"/api/v1/reports/{REPORT_ID}/decision",
            json={**base, "decision": "reject", "approved_position_codes": ["P1"]},
        )

    assert no_codes.status_code == 422
    assert reject_with_codes.status_code == 422


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (ReportNotFoundError(), 404),
        (ReportConflictError(), 409),
        (ReportGenerationError(), 502),
        (ReportWorkflowUnavailableError(), 503),
    ],
)
def test_report_errors_are_mapped(error: Exception, expected_status: int) -> None:
    with client_for(StubReportService(error)) as client:
        response = client.get(f"/api/v1/reports/{REPORT_ID}")

    assert response.status_code == expected_status


def test_report_endpoints_declare_bearer_security() -> None:
    paths = create_app().openapi()["paths"]

    assert paths["/api/v1/reports"]["post"]["security"] == [{"HTTPBearer": []}]
    assert paths["/api/v1/reports/{report_id}/decision"]["post"]["security"] == [{"HTTPBearer": []}]
    assert paths["/api/v1/reports/{report_id}"]["get"]["security"] == [{"HTTPBearer": []}]
