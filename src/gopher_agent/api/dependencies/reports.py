"""选岗报告 workflow dependencies。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, cast

from fastapi import Depends, Request

from gopher_agent.agents.report import build_report_graph
from gopher_agent.agents.runtime import AgentResources
from gopher_agent.api.dependencies.auth import get_user_repository
from gopher_agent.api.dependencies.positions import get_position_match_service
from gopher_agent.core.database import async_session_factory
from gopher_agent.repositories.protocols import (
    ReportRepositoryProtocol,
    UserRepositoryProtocol,
)
from gopher_agent.repositories.sqlalchemy.report import SqlAlchemyReportRepository
from gopher_agent.services.matching import PositionMatchService
from gopher_agent.services.report import ReportGraphProtocol, ReportService


@asynccontextmanager
async def open_report_repository() -> AsyncIterator[ReportRepositoryProtocol]:
    """为一次报告状态变更创建独立短 transaction。"""
    async with async_session_factory() as session, session.begin():
        yield SqlAlchemyReportRepository(session)


def get_report_service(
    request: Request,
    users: Annotated[UserRepositoryProtocol, Depends(get_user_repository)],
    matching: Annotated[PositionMatchService, Depends(get_position_match_service)],
) -> ReportService:
    """组装报告 Service；读取报告不强制要求 Agent 资源在线。"""
    resources = getattr(request.app.state, "agent_resources", None)
    graph: ReportGraphProtocol | None = None
    max_iterations = 10
    if resources is not None:
        typed_resources = cast(AgentResources, resources)
        compiled = build_report_graph(typed_resources.model, typed_resources.checkpointer)
        graph = cast(ReportGraphProtocol, compiled)
        max_iterations = typed_resources.max_iterations
    return ReportService(
        user_repository=users,
        matching=matching,
        repository_context=open_report_repository,
        graph=graph,
        max_iterations=max_iterations,
    )
