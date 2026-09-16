"""API 路由聚合。"""

from fastapi import APIRouter

from gopher_agent.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
