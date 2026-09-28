"""用户档案解析与确认 Application Service。"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from uuid import UUID, uuid4

from gopher_agent.agents.parser import ProfileParserProtocol
from gopher_agent.domain.enums import SessionStatus, UserMode
from gopher_agent.domain.profile import ProfileData
from gopher_agent.models.session import UserSession
from gopher_agent.repositories.protocols import ProfileRepositoryProtocol
from gopher_agent.services.exceptions import (
    ProfileParserUnavailableError,
    ProfileSessionConflictError,
    ProfileSessionNotFoundError,
)

type ProfileRepositoryContextFactory = Callable[
    [], AbstractAsyncContextManager[ProfileRepositoryProtocol]
]


@dataclass(frozen=True, slots=True)
class ProfileParseResult:
    """解析完成后返回给 transport 层的待确认草稿。"""

    session_id: UUID
    status: SessionStatus
    profile: ProfileData
    missing_fields: tuple[str, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProfileConfirmationResult:
    """用户确认后的权威档案结果。"""

    session_id: UUID
    status: SessionStatus
    profile: ProfileData


class ProfileService:
    """编排 Parser，并通过短 transaction 保存草稿和权威档案。"""

    def __init__(
        self,
        parser: ProfileParserProtocol | None,
        repository_context: ProfileRepositoryContextFactory,
    ) -> None:
        self._parser = parser
        self._repository_context = repository_context

    async def parse(
        self,
        *,
        user_id: int,
        mode: UserMode,
        content: str | None = None,
        profile: ProfileData | None = None,
    ) -> ProfileParseResult:
        """生成档案草稿；外部模型调用在数据库 transaction 之前完成。"""
        draft = await self._build_draft(mode=mode, content=content, profile=profile)
        session_id = uuid4()
        snapshot = draft.model_dump(mode="json")

        async with self._repository_context() as repository:
            user_session = UserSession(
                session_id=str(session_id),
                user_id=user_id,
                mode=mode.value,
                status=SessionStatus.PARSING.value,
                profile_snapshot={},
            )
            await repository.add_session(user_session)
            user_session.profile_snapshot = snapshot
            user_session.status = SessionStatus.CONFIRMING.value

        return ProfileParseResult(
            session_id=session_id,
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
        """加锁确认草稿，并原子更新 session 与权威档案。"""
        snapshot = profile.model_dump(mode="json")
        async with self._repository_context() as repository:
            user_session = await repository.get_owned_session_for_update(str(session_id), user_id)
            if user_session is None:
                raise ProfileSessionNotFoundError

            if user_session.status == SessionStatus.COMPLETED.value:
                if user_session.profile_snapshot != snapshot:
                    raise ProfileSessionConflictError
                return ProfileConfirmationResult(
                    session_id=session_id,
                    status=SessionStatus.COMPLETED,
                    profile=ProfileData.model_validate(user_session.profile_snapshot),
                )

            if user_session.status != SessionStatus.CONFIRMING.value:
                raise ProfileSessionConflictError

            user_session.profile_snapshot = snapshot
            user_session.status = SessionStatus.COMPLETED.value
            await repository.upsert_profile(user_id, snapshot)

        return ProfileConfirmationResult(
            session_id=session_id,
            status=SessionStatus.COMPLETED,
            profile=profile,
        )

    async def _build_draft(
        self,
        *,
        mode: UserMode,
        content: str | None,
        profile: ProfileData | None,
    ) -> ProfileData:
        """根据输入模式生成同一种档案 DTO。"""
        if mode is UserMode.ADVANCED:
            if profile is None:  # API schema 已保证，保留 service 层防御
                raise ValueError("advanced 模式必须提供 profile")
            return profile

        if self._parser is None:
            raise ProfileParserUnavailableError
        if content is None:  # API schema 已保证，保留 service 层防御
            raise ValueError("beginner 模式必须提供 content")
        return await self._parser.parse(content)
