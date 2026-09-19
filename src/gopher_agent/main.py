"""ASGI 应用入口。"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from gopher_agent import __version__
from gopher_agent.agents.runtime import open_agent_resources
from gopher_agent.api.router import api_router, root_router
from gopher_agent.core.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """按显式开关管理 Agent 外部资源，不影响其他 API 启动。"""
    settings = get_settings()
    application.state.agent_resources = None
    if not settings.agent_enabled:
        yield
        return

    resource_context = open_agent_resources(settings)
    try:
        resources = await resource_context.__aenter__()
    except Exception as error:
        logger.error(
            "Agent 资源初始化失败。Chat API 将返回 503。error_type=%s",
            type(error).__name__,
        )
        yield
        return

    application.state.agent_resources = resources
    try:
        yield
    finally:
        application.state.agent_resources = None
        await resource_context.__aexit__(None, None, None)


def create_app() -> FastAPI:
    """创建应用实例，便于测试时隔离全局状态。"""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version=__version__,
        lifespan=lifespan,
    )
    application.include_router(root_router)
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
