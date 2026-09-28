"""多轮档案 Interview 的确定性 Application Service。"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from uuid import UUID, uuid4

from pydantic import ValidationError

from gopher_agent.agents.parser import ProfileInterviewParserProtocol
from gopher_agent.domain.enums import SessionStatus, UserMode
from gopher_agent.domain.interview import (
    INTERVIEW_FIELDS,
    INTERVIEW_QUESTIONS,
    InterviewAnswerExtraction,
    InterviewField,
    InterviewState,
    InterviewStatus,
)
from gopher_agent.domain.profile import ProfileData
from gopher_agent.models.session import UserSession
from gopher_agent.repositories.protocols import ProfileRepositoryProtocol
from gopher_agent.services.exceptions import (
    ProfileInterviewConflictError,
    ProfileParserUnavailableError,
    ProfileSessionNotFoundError,
)

type InterviewRepositoryContextFactory = Callable[
    [], AbstractAsyncContextManager[ProfileRepositoryProtocol]
]


@dataclass(frozen=True, slots=True)
class ProfileInterviewResult:
    """返回给 transport 层的当前访谈视图。"""

    session_id: UUID
    interview_status: InterviewStatus
    question_id: UUID | None
    current_field: InterviewField | None
    question: str | None
    profile: ProfileData
    missing_fields: tuple[InterviewField, ...]
    skipped_fields: tuple[InterviewField, ...]


class ProfileInterviewService:
    """编排单字段 Parser 与 PostgreSQL 权威访谈状态。"""

    def __init__(
        self,
        parser: ProfileInterviewParserProtocol | None,
        repository_context: InterviewRepositoryContextFactory,
    ) -> None:
        self._parser = parser
        self._repository_context = repository_context

    async def start(
        self, *, user_id: int, session_id: UUID | None = None
    ) -> ProfileInterviewResult:
        """新建访谈，或初始化/继续本人待确认的解析 session。"""
        async with self._repository_context() as repository:
            if session_id is None:
                session_id = uuid4()
                stored_profile = await repository.get_profile_by_user_id(user_id)
                profile = ProfileData.model_validate(
                    stored_profile.profile if stored_profile is not None else {}
                )
                state = self._initial_state(profile)
                user_session = UserSession(
                    session_id=str(session_id),
                    user_id=user_id,
                    mode=UserMode.BEGINNER.value,
                    status=SessionStatus.CONFIRMING.value,
                    profile_snapshot=profile.model_dump(mode="json"),
                    interview_state=state.model_dump(mode="json"),
                )
                await repository.add_session(user_session)
                return self._result(session_id, profile, state)

            existing_session = await repository.get_owned_session_for_update(
                str(session_id), user_id
            )
            if existing_session is None:
                raise ProfileSessionNotFoundError
            self._ensure_confirming(existing_session)
            profile = ProfileData.model_validate(existing_session.profile_snapshot)
            if existing_session.interview_state:
                state = self._load_state(existing_session.interview_state)
            else:
                state = self._initial_state(profile)
                existing_session.interview_state = state.model_dump(mode="json")
            return self._result(session_id, profile, state)

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
        """在两段短事务之间解析回答，并通过问题版本防止并发覆盖。"""
        async with self._repository_context() as repository:
            user_session = await repository.get_owned_session_for_update(str(session_id), user_id)
            if user_session is None:
                raise ProfileSessionNotFoundError
            self._ensure_confirming(user_session)
            profile = ProfileData.model_validate(user_session.profile_snapshot)
            state = self._load_state_or_conflict(user_session.interview_state)
            if state.last_request_id == request_id:
                return self._result(session_id, profile, state)
            self._ensure_active_state(state)
            self._ensure_current_question(state, question_id)
            current_field = state.current_field
            if current_field is None:  # 防御：active state 已保证该字段存在
                raise ProfileInterviewConflictError

        extraction: InterviewAnswerExtraction | None = None
        if not skip:
            if self._parser is None:
                raise ProfileParserUnavailableError
            if answer is None:  # API schema 已保证，保留 service 层防御
                raise ValueError("非跳过请求必须提供 answer")
            extraction = await self._parser.parse_answer(current_field, answer)

        async with self._repository_context() as repository:
            user_session = await repository.get_owned_session_for_update(str(session_id), user_id)
            if user_session is None:
                raise ProfileSessionNotFoundError
            self._ensure_confirming(user_session)
            profile = ProfileData.model_validate(user_session.profile_snapshot)
            state = self._load_state_or_conflict(user_session.interview_state)
            if state.last_request_id == request_id:
                return self._result(session_id, profile, state)
            self._ensure_active_state(state)
            self._ensure_current_question(state, question_id, expected_field=current_field)

            if skip:
                if current_field not in state.skipped_fields:
                    state.skipped_fields.append(current_field)
                state = self._advance(profile, state, request_id=request_id)
            else:
                profile, state = self._merge_extraction(
                    profile, state, extraction, request_id=request_id
                )

            user_session.profile_snapshot = profile.model_dump(mode="json")
            user_session.interview_state = state.model_dump(mode="json")
            return self._result(session_id, profile, state)

    @staticmethod
    def _initial_state(profile: ProfileData) -> InterviewState:
        """从档案快照创建第一个问题或完成状态。"""
        seed = InterviewState(status=InterviewStatus.READY_TO_CONFIRM)
        return ProfileInterviewService._advance(profile, seed)

    @staticmethod
    def _advance(
        profile: ProfileData,
        state: InterviewState,
        *,
        request_id: UUID | None = None,
    ) -> InterviewState:
        """按固定字段顺序生成下一个问题。"""
        skipped = set(state.skipped_fields)
        next_field = next(
            (
                field
                for field in INTERVIEW_FIELDS
                if getattr(profile, field.value) is None and field not in skipped
            ),
            None,
        )
        if next_field is None:
            return state.model_copy(
                update={
                    "status": InterviewStatus.READY_TO_CONFIRM,
                    "current_field": None,
                    "question_id": None,
                    "last_request_id": request_id,
                }
            )

        asked_fields = list(state.asked_fields)
        turn = state.turn
        if next_field not in asked_fields:
            asked_fields.append(next_field)
            turn += 1
        return state.model_copy(
            update={
                "status": InterviewStatus.WAITING_ANSWER,
                "current_field": next_field,
                "question_id": uuid4(),
                "asked_fields": asked_fields,
                "turn": turn,
                "last_request_id": request_id,
            }
        )

    @staticmethod
    def _merge_extraction(
        profile: ProfileData,
        state: InterviewState,
        extraction: InterviewAnswerExtraction | None,
        *,
        request_id: UUID,
    ) -> tuple[ProfileData, InterviewState]:
        """只合并当前字段；未理解或校验失败时保留当前问题。"""
        current_field = state.current_field
        if (
            current_field is None
            or extraction is None
            or not extraction.understood
            or extraction.value is None
        ):
            return profile, state.model_copy(
                update={
                    "status": InterviewStatus.NEEDS_CLARIFICATION,
                    "last_request_id": request_id,
                }
            )

        candidate = profile.model_dump(mode="python")
        candidate[current_field.value] = extraction.value
        try:
            updated_profile = ProfileData.model_validate(candidate)
        except ValidationError:
            return profile, state.model_copy(
                update={
                    "status": InterviewStatus.NEEDS_CLARIFICATION,
                    "last_request_id": request_id,
                }
            )
        return updated_profile, ProfileInterviewService._advance(
            updated_profile, state, request_id=request_id
        )

    @staticmethod
    def _ensure_confirming(user_session: UserSession) -> None:
        if user_session.status != SessionStatus.CONFIRMING.value:
            raise ProfileInterviewConflictError

    @staticmethod
    def _load_state(raw_state: dict[str, object]) -> InterviewState:
        try:
            return InterviewState.model_validate(raw_state)
        except ValidationError as error:
            raise ProfileInterviewConflictError from error

    @staticmethod
    def _load_state_or_conflict(raw_state: dict[str, object]) -> InterviewState:
        if not raw_state:
            raise ProfileInterviewConflictError
        return ProfileInterviewService._load_state(raw_state)

    @staticmethod
    def _ensure_active_state(state: InterviewState) -> None:
        if (
            state.status is InterviewStatus.READY_TO_CONFIRM
            or state.current_field is None
            or state.question_id is None
        ):
            raise ProfileInterviewConflictError

    @staticmethod
    def _ensure_current_question(
        state: InterviewState,
        question_id: UUID,
        *,
        expected_field: InterviewField | None = None,
    ) -> None:
        if state.question_id != question_id or (
            expected_field is not None and state.current_field is not expected_field
        ):
            raise ProfileInterviewConflictError

    @staticmethod
    def _result(
        session_id: UUID, profile: ProfileData, state: InterviewState
    ) -> ProfileInterviewResult:
        question = (
            INTERVIEW_QUESTIONS[state.current_field] if state.current_field is not None else None
        )
        missing_fields = tuple(
            field for field in INTERVIEW_FIELDS if getattr(profile, field.value) is None
        )
        return ProfileInterviewResult(
            session_id=session_id,
            interview_status=state.status,
            question_id=state.question_id,
            current_field=state.current_field,
            question=question,
            profile=profile,
            missing_fields=missing_fields,
            skipped_fields=tuple(state.skipped_fields),
        )
