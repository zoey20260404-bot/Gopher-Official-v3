"""岗位检索相关 FastAPI dependencies。"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from gopher_agent.core.database import get_session
from gopher_agent.repositories.protocols import PositionRepositoryProtocol
from gopher_agent.repositories.sqlalchemy.position import SqlAlchemyPositionRepository
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
