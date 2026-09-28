"""用户档案 ProfileService 单元测试。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pytest

from gopher_agent.domain.enums import SessionStatus, UserMode
from gopher_agent.domain.profile import ProfileData
from gopher_agent.models.session import UserSession
from gopher_agent.models.user import UserProfile
from gopher_agent.repositories.protocols import ProfileRepositoryProtocol
from gopher_agent.services.exceptions import (
    ProfileParserUnavailableError,
    ProfileSessionConflictError,
    ProfileSessionNotFoundError,
)
from gopher_agent.services.profile import ProfileRepositoryContextFactory, ProfileService


class FakeParser:
    """返回固定草稿并记录输入。"""

    def __init__(self) -> None:
        self.content: str | None = None

    async def parse(self, content: str) -> ProfileData:
        self.content = content
        return ProfileData(education="本科", age=24)


class FakeProfileRepository:
    """在内存中模拟同一 transaction 内的档案操作。"""

    def __init__(self, user_session: UserSession | None = None) -> None:
        self.user_session = user_session
        self.upserted: tuple[int, dict[str, object]] | None = None

    async def add_session(self, user_session: UserSession) -> UserSession:
        self.user_session = user_session
        return user_session

    async def get_owned_session_for_update(
        self, session_id: str, user_id: int
    ) -> UserSession | None:
        if (
            self.user_session is not None
            and self.user_session.session_id == session_id
            and self.user_session.user_id == user_id
        ):
            return self.user_session
        return None

    async def get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        """ProfileService 当前不会读取权威档案。"""
        return None

    async def upsert_profile(self, user_id: int, profile: dict[str, object]) -> UserProfile:
        self.upserted = (user_id, profile)
        return UserProfile(user_id=user_id, profile=profile)


def repository_context(repository: FakeProfileRepository) -> ProfileRepositoryContextFactory:
    """创建符合 Service Protocol 的异步 repository context。"""

    @asynccontextmanager
    async def context() -> AsyncIterator[ProfileRepositoryProtocol]:
        yield repository

    return context


async def test_beginner_parse_uses_parser_and_saves_confirming_snapshot() -> None:
    parser = FakeParser()
    repository = FakeProfileRepository()
    service = ProfileService(parser, repository_context(repository))

    result = await service.parse(user_id=7, mode=UserMode.BEGINNER, content="我的信息")

    assert parser.content == "我的信息"
    assert result.status is SessionStatus.CONFIRMING
    assert result.profile.education == "本科"
    assert "major" in result.missing_fields
    assert repository.user_session is not None
    assert repository.user_session.user_id == 7
    assert repository.user_session.status == "confirming"
    assert repository.user_session.profile_snapshot["age"] == 24


async def test_advanced_parse_does_not_require_parser() -> None:
    repository = FakeProfileRepository()
    service = ProfileService(None, repository_context(repository))

    result = await service.parse(
        user_id=7,
        mode=UserMode.ADVANCED,
        profile=ProfileData(major="计算机"),
    )

    assert result.profile.major == "计算机"
    assert repository.user_session is not None
    assert repository.user_session.mode == "advanced"


async def test_beginner_parse_requires_available_parser() -> None:
    service = ProfileService(None, repository_context(FakeProfileRepository()))

    with pytest.raises(ProfileParserUnavailableError):
        await service.parse(user_id=7, mode=UserMode.BEGINNER, content="本科")


async def test_confirm_upserts_profile_and_is_idempotent_for_same_snapshot() -> None:
    session_id = uuid4()
    user_session = UserSession(
        session_id=str(session_id),
        user_id=7,
        mode="advanced",
        status="confirming",
        profile_snapshot={},
    )
    repository = FakeProfileRepository(user_session)
    service = ProfileService(None, repository_context(repository))
    profile = ProfileData(education="本科")

    result = await service.confirm(user_id=7, session_id=session_id, profile=profile)
    repeated = await service.confirm(user_id=7, session_id=session_id, profile=profile)

    assert result.status is SessionStatus.COMPLETED
    assert repeated.profile == profile
    assert user_session.status == "completed"
    assert repository.upserted == (7, profile.model_dump(mode="json"))


async def test_confirm_hides_other_users_and_rejects_changed_completed_profile() -> None:
    session_id = UUID("0199d418-9f9a-7000-8000-000000000001")
    user_session = UserSession(
        session_id=str(session_id),
        user_id=8,
        mode="advanced",
        status="completed",
        profile_snapshot=ProfileData(age=24).model_dump(mode="json"),
    )
    service = ProfileService(None, repository_context(FakeProfileRepository(user_session)))

    with pytest.raises(ProfileSessionNotFoundError):
        await service.confirm(user_id=7, session_id=session_id, profile=ProfileData(age=24))
    with pytest.raises(ProfileSessionConflictError):
        await service.confirm(user_id=8, session_id=session_id, profile=ProfileData(age=25))
