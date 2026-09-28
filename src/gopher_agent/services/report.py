"""选岗报告创建、人工审批与 LangGraph 恢复编排。"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol, cast
from uuid import UUID, uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command

from gopher_agent.domain.enums import ReportStatus
from gopher_agent.domain.matching import PositionMatchFilter, RuleResult
from gopher_agent.domain.profile import ProfileData
from gopher_agent.domain.report import (
    GeneratedReport,
    ReportApproval,
    ReportCandidate,
    ReportDecision,
    ReportProposal,
    ReportReason,
)
from gopher_agent.models.report import Report
from gopher_agent.repositories.protocols import (
    ReportRepositoryProtocol,
    UserRepositoryProtocol,
)
from gopher_agent.services.exceptions import (
    ReportConflictError,
    ReportGenerationError,
    ReportNoCandidatesError,
    ReportNotFoundError,
    ReportWorkflowUnavailableError,
    UserProfileNotConfirmedError,
)
from gopher_agent.services.matching import (
    PositionMatchItem,
    PositionMatchQuery,
    PositionMatchService,
)

type ReportRepositoryContextFactory = Callable[
    [], AbstractAsyncContextManager[ReportRepositoryProtocol]
]


class ReportGraphProtocol(Protocol):
    """ReportService 所需的最小 compiled graph 能力。"""

    async def ainvoke(self, input: object, config: RunnableConfig) -> dict[str, object]:
        """运行至 interrupt，或使用 Command 恢复执行。"""
        ...


@dataclass(frozen=True, slots=True)
class ReportCreateQuery:
    """transport 无关的报告候选过滤条件。"""

    exam_type: str | None = None
    year: int | None = None
    province: str | None = None
    city: str | None = None
    keyword: str | None = None
    max_candidates: int = 10


@dataclass(frozen=True, slots=True)
class ReportView:
    """返回 API 层的报告业务视图。"""

    report_id: UUID
    status: ReportStatus
    proposal: ReportProposal | None
    approval: ReportApproval | None
    generated_report: GeneratedReport | None
    content: str


class ReportService:
    """协调确定性岗位匹配、报告持久化和可恢复 graph。"""

    def __init__(
        self,
        *,
        user_repository: UserRepositoryProtocol,
        matching: PositionMatchService,
        repository_context: ReportRepositoryContextFactory,
        graph: ReportGraphProtocol | None,
        max_iterations: int,
    ) -> None:
        self._users = user_repository
        self._matching = matching
        self._repository_context = repository_context
        self._graph = graph
        self._max_iterations = max_iterations

    async def create(self, *, user_id: int, query: ReportCreateQuery) -> ReportView:
        """创建报告，保存事实快照并运行 graph 至人工审批暂停点。"""
        graph = self._require_graph()
        stored_profile = await self._users.get_profile_by_user_id(user_id)
        if stored_profile is None:
            raise UserProfileNotConfirmedError
        profile = ProfileData.model_validate(stored_profile.profile)
        matches = await self._matching.search(
            user_id,
            PositionMatchQuery(
                exam_type=query.exam_type,
                year=query.year,
                province=query.province,
                city=query.city,
                keyword=query.keyword,
                match_filter=PositionMatchFilter.POTENTIAL,
                page=1,
                page_size=query.max_candidates,
            ),
        )
        candidates = [self._candidate(item) for item in matches.items]
        if not candidates:
            raise ReportNoCandidatesError
        proposal = ReportProposal(candidates=candidates)
        report_id = uuid4()
        request_snapshot = {
            "exam_type": query.exam_type,
            "year": query.year,
            "province": query.province,
            "city": query.city,
            "keyword": query.keyword,
            "max_candidates": query.max_candidates,
        }
        result: dict[str, object] = {"proposal": proposal.model_dump(mode="json")}
        report = Report(
            report_id=str(report_id),
            user_id=user_id,
            session_id=str(report_id),
            profile_snapshot=profile.model_dump(mode="json"),
            request_snapshot=request_snapshot,
            content="",
            result=result,
            status=ReportStatus.PROCESSING.value,
        )
        async with self._repository_context() as repository:
            await repository.add(report)

        graph_input = {
            "report_id": str(report_id),
            "profile": profile.model_dump(mode="json"),
            "candidates": proposal.model_dump(mode="json")["candidates"],
        }
        try:
            output = await graph.ainvoke(graph_input, self._config(user_id, report_id))
            if "__interrupt__" not in output:
                raise ReportConflictError
        except Exception as error:
            await self._mark_failed(user_id, report_id)
            raise ReportGenerationError from error

        async with self._repository_context() as repository:
            stored = await repository.get_owned_for_update(str(report_id), user_id)
            if stored is None:
                raise ReportNotFoundError
            if stored.status != ReportStatus.PROCESSING.value:
                raise ReportConflictError
            stored.status = ReportStatus.PENDING_APPROVAL.value
            return self._view(stored)

    async def decide(
        self,
        *,
        user_id: int,
        report_id: UUID,
        request_id: UUID,
        approval: ReportApproval,
    ) -> ReportView:
        """原子领取审批请求，在事务外恢复 graph，再持久化最终结果。"""
        async with self._repository_context() as repository:
            report = await repository.get_owned_for_update(str(report_id), user_id)
            if report is None:
                raise ReportNotFoundError
            if report.last_request_id == str(request_id) and report.status in {
                ReportStatus.COMPLETED.value,
                ReportStatus.REJECTED.value,
            }:
                return self._view(report)
            if report.status != ReportStatus.PENDING_APPROVAL.value:
                raise ReportConflictError
            graph = self._require_graph()
            proposal = self._proposal(report)
            self._validate_approval(proposal, approval)
            result = dict(report.result)
            result["approval"] = approval.model_dump(mode="json")
            report.result = result
            report.last_request_id = str(request_id)
            report.status = ReportStatus.PROCESSING.value

        try:
            output = await graph.ainvoke(
                Command(resume=approval.model_dump(mode="json")),
                self._config(user_id, report_id),
            )
            generated = self._validate_graph_output(output, approval)
        except Exception as error:
            await self._mark_failed(user_id, report_id, request_id=request_id)
            if isinstance(error, ReportConflictError):
                raise
            raise ReportGenerationError from error

        async with self._repository_context() as repository:
            report = await repository.get_owned_for_update(str(report_id), user_id)
            if report is None:
                raise ReportNotFoundError
            if report.status != ReportStatus.PROCESSING.value or report.last_request_id != str(
                request_id
            ):
                raise ReportConflictError
            result = dict(report.result)
            if generated is None:
                report.status = ReportStatus.REJECTED.value
            else:
                result["generated_report"] = generated.model_dump(mode="json")
                report.content = self._render_content(self._proposal(report), generated)
                report.status = ReportStatus.COMPLETED.value
            report.result = result
            return self._view(report)

    def _require_graph(self) -> ReportGraphProtocol:
        if self._graph is None:
            raise ReportWorkflowUnavailableError
        return self._graph

    async def get(self, *, user_id: int, report_id: UUID) -> ReportView:
        """读取当前用户的报告。"""
        async with self._repository_context() as repository:
            report = await repository.get_owned(str(report_id), user_id)
            if report is None:
                raise ReportNotFoundError
            return self._view(report)

    async def _mark_failed(
        self, user_id: int, report_id: UUID, *, request_id: UUID | None = None
    ) -> None:
        """尽力把当前执行标记为失败，不覆盖其他并发状态。"""
        async with self._repository_context() as repository:
            report = await repository.get_owned_for_update(str(report_id), user_id)
            if report is None or report.status != ReportStatus.PROCESSING.value:
                return
            if request_id is not None and report.last_request_id != str(request_id):
                return
            report.status = ReportStatus.FAILED.value

    def _config(self, user_id: int, report_id: UUID) -> RunnableConfig:
        return cast(
            RunnableConfig,
            {
                "configurable": {"thread_id": self.thread_id(user_id, report_id)},
                "recursion_limit": self._max_iterations,
            },
        )

    @staticmethod
    def thread_id(user_id: int, report_id: UUID) -> str:
        """隔离不同用户和报告的 checkpoint namespace。"""
        return f"user:{user_id}:report:{report_id}"

    @staticmethod
    def _candidate(item: object) -> ReportCandidate:
        if not isinstance(item, PositionMatchItem):
            raise TypeError("岗位匹配结果类型无效")
        position = item.position
        return ReportCandidate(
            position_code=position.position_code,
            position_name=position.position_name,
            department=position.department,
            exam_type=position.exam_type,
            year=position.year,
            province=position.province,
            city=position.city,
            match_status=item.match_status,
            missing_profile_fields=list(item.missing_profile_fields),
            reasons=[
                ReportReason(
                    field=reason.field,
                    result=reason.result,
                    code=reason.code,
                    message=reason.message,
                    profile_value=reason.profile_value,
                    requirement=reason.requirement,
                )
                for reason in item.reasons
                if reason.result is not RuleResult.PASS
            ],
            score_latest=position.score_latest,
            score_year=position.score_year,
            applicant_ratio_2025=position.applicant_ratio_2025,
        )

    @staticmethod
    def _validate_approval(proposal: ReportProposal, approval: ReportApproval) -> None:
        approved = approval.approved_position_codes
        if len(set(approved)) != len(approved):
            raise ReportConflictError
        if approval.decision is ReportDecision.REJECT:
            if approved:
                raise ReportConflictError
            return
        if not approved:
            raise ReportConflictError
        candidate_codes = {item.position_code for item in proposal.candidates}
        if not set(approved).issubset(candidate_codes):
            raise ReportConflictError

    @staticmethod
    def _validate_graph_output(
        output: dict[str, object], approval: ReportApproval
    ) -> GeneratedReport | None:
        if approval.decision is ReportDecision.REJECT:
            resumed_approval = ReportApproval.model_validate(output.get("approval"))
            if resumed_approval != approval:
                raise ReportConflictError
            return None
        if output.get("workflow_status") != ReportStatus.COMPLETED.value:
            raise ReportConflictError
        generated = GeneratedReport.model_validate(output.get("generated_report"))
        actual = [item.position_code for item in generated.positions]
        if len(actual) != len(set(actual)) or set(actual) != set(approval.approved_position_codes):
            raise ReportConflictError
        return generated

    @staticmethod
    def _proposal(report: Report) -> ReportProposal:
        proposal = report.result.get("proposal")
        if proposal is None:
            raise ReportConflictError
        return ReportProposal.model_validate(proposal)

    @staticmethod
    def _view(report: Report) -> ReportView:
        result = report.result
        proposal_raw = result.get("proposal")
        approval_raw = result.get("approval")
        generated_raw = result.get("generated_report")
        return ReportView(
            report_id=UUID(report.report_id),
            status=ReportStatus(report.status),
            proposal=(
                ReportProposal.model_validate(proposal_raw) if proposal_raw is not None else None
            ),
            approval=(
                ReportApproval.model_validate(approval_raw) if approval_raw is not None else None
            ),
            generated_report=(
                GeneratedReport.model_validate(generated_raw) if generated_raw is not None else None
            ),
            content=report.content,
        )

    @staticmethod
    def _render_content(proposal: ReportProposal, generated: GeneratedReport) -> str:
        candidates = {item.position_code: item for item in proposal.candidates}
        lines = [f"# {generated.title}", "", generated.overview]
        for advice in generated.positions:
            candidate = candidates[advice.position_code]
            category = "优先考虑" if candidate.match_status.value == "eligible" else "需要复核"
            lines.extend(
                [
                    "",
                    f"## {candidate.position_name} ({candidate.position_code})",
                    "",
                    f"- 分类: {category}",
                    f"- 部门: {candidate.department}",
                    f"- 建议: {advice.summary}",
                    "- 下一步: " + "; ".join(advice.action_items),
                ]
            )
        return "\n".join(lines)
