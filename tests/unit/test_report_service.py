"""ReportService 业务状态与幂等单元测试。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast
from uuid import uuid4

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from gopher_agent.domain.enums import ReportStatus
from gopher_agent.domain.matching import PositionMatchStatus
from gopher_agent.domain.profile import ProfileData
from gopher_agent.domain.report import ReportApproval, ReportDecision
from gopher_agent.models.report import Report
from gopher_agent.models.user import User, UserProfile
from gopher_agent.repositories.protocols import ReportRepositoryProtocol
from gopher_agent.services.exceptions import (
    ReportConflictError,
    ReportNoCandidatesError,
    ReportWorkflowUnavailableError,
)
from gopher_agent.services.matching import (
    PositionMatchItem,
    PositionMatchQuery,
    PositionMatchResult,
    PositionMatchService,
)
from gopher_agent.services.positions import PositionItem
from gopher_agent.services.report import (
    ReportCreateQuery,
    ReportGraphProtocol,
    ReportRepositoryContextFactory,
    ReportService,
)


class FakeUserRepository:
    """返回固定权威档案。"""

    def __init__(self, profile: UserProfile | None) -> None:
        self.profile = profile

    async def add(self, user: User) -> User:
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        return None

    async def get_by_username(self, username: str) -> User | None:
        return None

    async def get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        return self.profile


class FakeMatchingService:
    """记录报告使用的确定性匹配查询。"""

    def __init__(self, items: list[PositionMatchItem]) -> None:
        self.items = items
        self.query: PositionMatchQuery | None = None

    async def search(self, user_id: int, query: PositionMatchQuery) -> PositionMatchResult:
        self.query = query
        return PositionMatchResult(
            items=self.items,
            total=len(self.items),
            page=1,
            page_size=query.page_size,
        )


class FakeReportRepository:
    """跨短事务共享同一内存报告。"""

    def __init__(self) -> None:
        self.report: Report | None = None

    async def add(self, report: Report) -> Report:
        self.report = report
        return report

    async def get_owned(self, report_id: str, user_id: int) -> Report | None:
        return self._owned(report_id, user_id)

    async def get_owned_for_update(self, report_id: str, user_id: int) -> Report | None:
        return self._owned(report_id, user_id)

    def _owned(self, report_id: str, user_id: int) -> Report | None:
        if (
            self.report is not None
            and self.report.report_id == report_id
            and self.report.user_id == user_id
        ):
            return self.report
        return None


class FakeReportGraph:
    """模拟首次 interrupt 与恢复后的终态。"""

    def __init__(self) -> None:
        self.calls: list[object] = []

    async def ainvoke(self, input: object, config: RunnableConfig) -> dict[str, object]:
        self.calls.append(input)
        if not isinstance(input, Command):
            return {"__interrupt__": ()}
        approval = ReportApproval.model_validate(input.resume)
        if approval.decision is ReportDecision.REJECT:
            return {"approval": approval.model_dump(mode="json")}
        return {
            "approval": approval.model_dump(mode="json"),
            "workflow_status": "completed",
            "generated_report": {
                "title": "选岗建议",
                "overview": "基于确定性资格匹配生成。",
                "positions": [
                    {
                        "position_code": code,
                        "summary": "满足已校验的硬条件。",
                        "action_items": ["核对公告原文"],
                    }
                    for code in approval.approved_position_codes
                ],
            },
        }


def repository_context(repository: FakeReportRepository) -> ReportRepositoryContextFactory:
    @asynccontextmanager
    async def context() -> AsyncIterator[ReportRepositoryProtocol]:
        yield repository

    return context


def build_position() -> PositionItem:
    return PositionItem(
        id=1,
        exam_type="国考",
        year=2026,
        province="广东",
        city="广州",
        department="税务局",
        position_name="一级行政执法员",
        position_code="P1",
        education_req="本科及以上",
        major_req_exact="不限",
        major_req_category="",
        political_req="不限",
        fresh_graduate_req=None,
        work_experience_years_req=0,
        gender_req="不限",
        age_limit=35,
        household_registration_req="不限",
        other_restrictions=[],
        remarks="",
        score_2025=None,
        score_2024=None,
        score_latest=None,
        score_year=None,
        applicant_ratio_2025="",
    )


def build_match() -> PositionMatchItem:
    return PositionMatchItem(
        position=build_position(),
        match_status=PositionMatchStatus.ELIGIBLE,
        reasons=(),
        missing_profile_fields=(),
    )


def build_service(
    *,
    matches: list[PositionMatchItem] | None = None,
    graph: FakeReportGraph | None = None,
) -> tuple[ReportService, FakeReportRepository, FakeReportGraph, FakeMatchingService]:
    repository = FakeReportRepository()
    fake_graph = graph or FakeReportGraph()
    matching = FakeMatchingService([build_match()] if matches is None else matches)
    profile = UserProfile(
        user_id=7,
        profile=ProfileData(education="本科", age=24).model_dump(mode="json"),
    )
    service = ReportService(
        user_repository=FakeUserRepository(profile),
        matching=cast(PositionMatchService, cast(Any, matching)),
        repository_context=repository_context(repository),
        graph=cast(ReportGraphProtocol, fake_graph),
        max_iterations=8,
    )
    return service, repository, fake_graph, matching


async def test_create_pauses_with_deterministic_candidate_proposal() -> None:
    service, repository, graph, matching = build_service()

    result = await service.create(
        user_id=7,
        query=ReportCreateQuery(province="广东", max_candidates=5),
    )

    assert result.status is ReportStatus.PENDING_APPROVAL
    assert result.proposal is not None
    assert result.proposal.candidates[0].position_code == "P1"
    assert matching.query is not None
    assert matching.query.page_size == 5
    assert repository.report is not None
    assert repository.report.profile_snapshot["age"] == 24
    assert len(graph.calls) == 1


async def test_approve_completes_report_and_same_request_is_idempotent() -> None:
    service, repository, graph, matching = build_service()
    created = await service.create(user_id=7, query=ReportCreateQuery())
    request_id = uuid4()
    approval = ReportApproval(
        decision=ReportDecision.APPROVE,
        approved_position_codes=["P1"],
    )

    completed = await service.decide(
        user_id=7,
        report_id=created.report_id,
        request_id=request_id,
        approval=approval,
    )
    service_without_graph = ReportService(
        user_repository=FakeUserRepository(
            UserProfile(user_id=7, profile=ProfileData().model_dump(mode="json"))
        ),
        matching=cast(PositionMatchService, cast(Any, matching)),
        repository_context=repository_context(repository),
        graph=None,
        max_iterations=8,
    )
    repeated = await service_without_graph.decide(
        user_id=7,
        report_id=created.report_id,
        request_id=request_id,
        approval=approval,
    )

    assert completed.status is ReportStatus.COMPLETED
    assert completed.generated_report is not None
    assert "一级行政执法员" in completed.content
    assert repeated == completed
    assert len(graph.calls) == 2


async def test_reject_ends_without_generated_report() -> None:
    service, _, _, _ = build_service()
    created = await service.create(user_id=7, query=ReportCreateQuery())

    rejected = await service.decide(
        user_id=7,
        report_id=created.report_id,
        request_id=uuid4(),
        approval=ReportApproval(decision=ReportDecision.REJECT),
    )

    assert rejected.status is ReportStatus.REJECTED
    assert rejected.generated_report is None
    assert rejected.content == ""


async def test_decision_rejects_codes_outside_proposal() -> None:
    service, _, _, _ = build_service()
    created = await service.create(user_id=7, query=ReportCreateQuery())

    with pytest.raises(ReportConflictError):
        await service.decide(
            user_id=7,
            report_id=created.report_id,
            request_id=uuid4(),
            approval=ReportApproval(
                decision=ReportDecision.APPROVE,
                approved_position_codes=["UNKNOWN"],
            ),
        )


async def test_create_rejects_empty_candidates_and_unavailable_graph() -> None:
    empty_service, _, _, _ = build_service(matches=[])
    with pytest.raises(ReportNoCandidatesError):
        await empty_service.create(user_id=7, query=ReportCreateQuery())

    _, repository, _, matching = build_service()
    profile = UserProfile(
        user_id=7,
        profile=ProfileData(education="本科", age=24).model_dump(mode="json"),
    )
    unavailable = ReportService(
        user_repository=FakeUserRepository(profile),
        matching=cast(PositionMatchService, cast(Any, matching)),
        repository_context=repository_context(repository),
        graph=None,
        max_iterations=8,
    )
    with pytest.raises(ReportWorkflowUnavailableError):
        await unavailable.create(user_id=7, query=ReportCreateQuery())
