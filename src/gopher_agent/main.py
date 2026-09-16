"""ASGI 应用入口。"""

from fastapi import FastAPI

from gopher_agent import __version__
from gopher_agent.api.router import api_router
from gopher_agent.core.config import get_settings


def create_app() -> FastAPI:
    """创建应用实例，便于测试时隔离全局状态。"""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version=__version__,
    )
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
