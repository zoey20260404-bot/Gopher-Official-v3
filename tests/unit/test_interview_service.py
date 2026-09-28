"""ProfileInterviewService 单元测试。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pytest

from gopher_agent.domain.interview import (
    InterviewAnswerExtraction,
    InterviewField,
    InterviewStatus,
)
from gopher_agent.models.session import UserSession
from gopher_agent.models.user import UserProfile
from gopher_agent.repositories.protocols import ProfileRepositoryProtocol
from gopher_agent.services.exceptions import (
    ProfileInterviewConflictError,
    ProfileParserUnavailableError,
    ProfileSessionNotFoundError,
)
from gopher_agent.services.interview import (
    InterviewRepositoryContextFactory,
    ProfileInterviewService,
)


class FakeInterviewParser:
    """返回可配置的单字段提取结果。"""

    def __init__(self, extraction: InterviewAnswerExtraction) -> None:
        self.extraction = extraction
        self.calls: list[tuple[InterviewField, str]] = []

    async def parse_answer(self, field: InterviewField, answer: str) -> InterviewAnswerExtraction:
        self.calls.append((field, answer))
        return self.extraction


class FakeInterviewRepository:
    """跨两段 context 保留同一内存状态。"""

    def __init__(self, profile: UserProfile | None = None) -> None:
        self.profile = profile
        self.session: UserSession | None = None

    async def add_session(self, user_session: UserSession) -> UserSession:
        self.session = user_session
        return user_session

    async def get_owned_session_for_update(
        self, session_id: str, user_id: int
    ) -> UserSession | None:
        if (
            self.session is not None
            and self.session.session_id == session_id
            and self.session.user_id == user_id
        ):
            return self.session
        return None

    async def get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        if self.profile is not None and self.profile.user_id == user_id:
            return self.profile
        return None

    async def upsert_profile(self, user_id: int, profile: dict[str, object]) -> UserProfile:
        raise AssertionError("访谈不应写入权威档案")


def repository_context(
    repository: FakeInterviewRepository,
) -> InterviewRepositoryContextFactory:
    @asynccontextmanager
    async def context() -> AsyncIterator[ProfileRepositoryProtocol]:
        yield repository

    return context


async def test_start_seeds_authoritative_profile_and_asks_first_missing_field() -> None:
    stored = UserProfile(user_id=7, profile={"education": "本科", "age": 24})
    repository = FakeInterviewRepository(stored)
    service = ProfileInterviewService(None, repository_context(repository))

    result = await service.start(user_id=7)

    assert result.profile.education == "本科"
    assert result.current_field is InterviewField.MAJOR
    assert result.interview_status is InterviewStatus.WAITING_ANSWER
    assert result.question_id is not None
    assert repository.session is not None
    assert repository.session.status == "confirming"
    assert repository.session.profile_snapshot["age"] == 24


async def test_answer_merges_only_current_field_and_advances() -> None:
    parser = FakeInterviewParser(InterviewAnswerExtraction(understood=True, value="本科"))
    repository = FakeInterviewRepository()
    service = ProfileInterviewService(parser, repository_context(repository))
    started = await service.start(user_id=7)
    request_id = uuid4()

    result = await service.answer(
        user_id=7,
        session_id=started.session_id,
        question_id=started.question_id or uuid4(),
        request_id=request_id,
        answer="本科毕业",
        skip=False,
    )

    assert parser.calls == [(InterviewField.EDUCATION, "本科毕业")]
    assert result.profile.education == "本科"
    assert result.current_field is InterviewField.MAJOR
    assert result.question_id != started.question_id

    repeated = await service.answer(
        user_id=7,
        session_id=started.session_id,
        question_id=started.question_id or uuid4(),
        request_id=request_id,
        answer="不会再次解析",
        skip=False,
    )
    assert repeated == result
    assert len(parser.calls) == 1


async def test_unrecognized_answer_keeps_question() -> None:
    parser = FakeInterviewParser(InterviewAnswerExtraction(understood=False, value=None))
    repository = FakeInterviewRepository()
    service = ProfileInterviewService(parser, repository_context(repository))
    started = await service.start(user_id=7)

    unclear = await service.answer(
        user_id=7,
        session_id=started.session_id,
        question_id=started.question_id or uuid4(),
        request_id=uuid4(),
        answer="不知道",
        skip=False,
    )

    assert unclear.interview_status is InterviewStatus.NEEDS_CLARIFICATION
    assert unclear.question_id == started.question_id
    assert unclear.current_field is InterviewField.EDUCATION


async def test_invalid_extracted_value_keeps_current_question() -> None:
    profile = UserProfile(
        user_id=7,
        profile={
            "education": "本科",
            "major": "计算机",
            "political_status": "群众",
            "fresh_graduate": False,
            "work_experience_years": 2,
            "gender": "女",
        },
    )
    parser = FakeInterviewParser(InterviewAnswerExtraction(understood=True, value=10))
    service = ProfileInterviewService(parser, repository_context(FakeInterviewRepository(profile)))
    started = await service.start(user_id=7)

    invalid = await service.answer(
        user_id=7,
        session_id=started.session_id,
        question_id=started.question_id or uuid4(),
        request_id=uuid4(),
        answer="10",
        skip=False,
    )
    assert invalid.interview_status is InterviewStatus.NEEDS_CLARIFICATION
    assert invalid.profile.age is None
    assert invalid.current_field is InterviewField.AGE


async def test_skip_works_without_parser_and_stale_question_conflicts() -> None:
    repository = FakeInterviewRepository()
    service = ProfileInterviewService(None, repository_context(repository))
    started = await service.start(user_id=7)

    skipped = await service.answer(
        user_id=7,
        session_id=started.session_id,
        question_id=started.question_id or uuid4(),
        request_id=uuid4(),
        answer=None,
        skip=True,
    )

    assert skipped.current_field is InterviewField.MAJOR
    assert skipped.skipped_fields == (InterviewField.EDUCATION,)
    assert skipped.profile.education is None

    with pytest.raises(ProfileInterviewConflictError):
        await service.answer(
            user_id=7,
            session_id=started.session_id,
            question_id=started.question_id or uuid4(),
            request_id=uuid4(),
            answer=None,
            skip=True,
        )

    with pytest.raises(ProfileParserUnavailableError):
        await service.answer(
            user_id=7,
            session_id=started.session_id,
            question_id=skipped.question_id or uuid4(),
            request_id=uuid4(),
            answer="计算机",
            skip=False,
        )


async def test_completed_profile_starts_ready_to_confirm() -> None:
    complete = {
        "education": "本科",
        "major": "计算机",
        "political_status": "群众",
        "fresh_graduate": False,
        "work_experience_years": 2,
        "gender": "女",
        "age": 24,
        "household_registration": "广东广州",
    }
    repository = FakeInterviewRepository(UserProfile(user_id=7, profile=complete))
    result = await ProfileInterviewService(None, repository_context(repository)).start(user_id=7)

    assert result.interview_status is InterviewStatus.READY_TO_CONFIRM
    assert result.question_id is None
    assert result.current_field is None
    assert result.question is None
    assert result.missing_fields == ()


async def test_last_answer_request_is_idempotent_after_ready_to_confirm() -> None:
    repository = FakeInterviewRepository()
    service = ProfileInterviewService(None, repository_context(repository))
    current = await service.start(user_id=7)
    final_question_id = current.question_id
    final_request_id = uuid4()

    for index in range(len(InterviewField)):
        final_question_id = current.question_id
        final_request_id = uuid4()
        current = await service.answer(
            user_id=7,
            session_id=current.session_id,
            question_id=final_question_id or uuid4(),
            request_id=final_request_id,
            answer=None,
            skip=True,
        )
        if index < len(InterviewField) - 1:
            assert current.interview_status is InterviewStatus.WAITING_ANSWER

    assert current.interview_status is InterviewStatus.READY_TO_CONFIRM
    repeated = await service.answer(
        user_id=7,
        session_id=current.session_id,
        question_id=final_question_id or uuid4(),
        request_id=final_request_id,
        answer=None,
        skip=True,
    )
    assert repeated == current


async def test_start_continues_existing_session_without_replacing_question() -> None:
    repository = FakeInterviewRepository()
    service = ProfileInterviewService(None, repository_context(repository))
    first = await service.start(user_id=7)
    continued = await service.start(user_id=7, session_id=first.session_id)

    assert continued == first

    unknown_id = UUID("0199d418-9f9a-7000-8000-000000000099")
    with pytest.raises(ProfileSessionNotFoundError):
        await service.start(user_id=7, session_id=unknown_id)
