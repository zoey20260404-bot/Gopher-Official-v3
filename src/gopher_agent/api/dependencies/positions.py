"""岗位检索相关 FastAPI dependencies。"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from gopher_agent.api.dependencies.auth import get_user_repository
from gopher_agent.core.config import Settings, get_settings
from gopher_agent.core.database import get_session
from gopher_agent.repositories.protocols import (
    PositionMatchRepositoryProtocol,
    PositionRepositoryProtocol,
    UserRepositoryProtocol,
)
from gopher_agent.repositories.sqlalchemy.position import SqlAlchemyPositionRepository
from gopher_agent.services.matching import PositionEligibilityEvaluator, PositionMatchService
from gopher_agent.services.positions import PositionSearchService


def get_position_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PositionRepositoryProtocol:
    """为当前请求创建岗位 Repository。"""
    return SqlAlchemyPositionRepository(session)


def get_position_search_service(
    positions: Annotated[PositionRepositoryProtocol, Depends(get_position_repository)],
) -> PositionSearchService:
    """组装岗位检索 Application Service。"""
    return PositionSearchService(positions)


def get_position_match_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PositionMatchRepositoryProtocol:
    """为资格匹配创建支持有界候选读取的 Repository。"""
    return SqlAlchemyPositionRepository(session)


def get_position_match_service(
    users: Annotated[UserRepositoryProtocol, Depends(get_user_repository)],
    positions: Annotated[PositionMatchRepositoryProtocol, Depends(get_position_match_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PositionMatchService:
    """组装共享请求级 session 的确定性岗位匹配 Service。"""
    return PositionMatchService(
        users,
        positions,
        PositionEligibilityEvaluator(),
        settings.position_match_candidate_limit,
    )
