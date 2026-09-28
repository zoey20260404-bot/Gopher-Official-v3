"""用户档案解析与确认 dependencies。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

from fastapi import Request

from gopher_agent.agents.parser import StructuredProfileInterviewParser, StructuredProfileParser
from gopher_agent.agents.runtime import AgentResources
from gopher_agent.core.database import async_session_factory
from gopher_agent.repositories.protocols import ProfileRepositoryProtocol
from gopher_agent.repositories.sqlalchemy.profile import SqlAlchemyProfileRepository
from gopher_agent.services.interview import ProfileInterviewService
from gopher_agent.services.profile import ProfileService


@asynccontextmanager
async def open_profile_repository() -> AsyncIterator[ProfileRepositoryProtocol]:
    """为一次档案写用例创建独立且自动提交/回滚的 transaction。"""
    async with async_session_factory() as session, session.begin():
        yield SqlAlchemyProfileRepository(session)


def get_profile_service(request: Request) -> ProfileService:
    """组装可选 Parser；advanced 模式不要求 Agent 资源。"""
    resources = getattr(request.app.state, "agent_resources", None)
    parser = None
    if resources is not None:
        typed_resources = cast(AgentResources, resources)
        parser = StructuredProfileParser(typed_resources.model)
    return ProfileService(parser, open_profile_repository)


def get_profile_interview_service(request: Request) -> ProfileInterviewService:
    """组装可选单字段 Parser；开始和跳过访谈不依赖模型资源。"""
    resources = getattr(request.app.state, "agent_resources", None)
    parser = None
    if resources is not None:
        typed_resources = cast(AgentResources, resources)
        parser = StructuredProfileInterviewParser(typed_resources.model)
    return ProfileInterviewService(parser, open_profile_repository)
