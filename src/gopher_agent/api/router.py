"""API 路由聚合。"""

from fastapi import APIRouter

from gopher_agent.api.routes.auth import router as auth_router
from gopher_agent.api.routes.chat import router as chat_router
from gopher_agent.api.routes.health import router as health_router
from gopher_agent.api.routes.positions import router as positions_router
from gopher_agent.api.routes.profile import router as profile_router

root_router = APIRouter()
root_router.include_router(auth_router)
api_router = APIRouter()
api_router.include_router(health_router, tags=["system"])
api_router.include_router(profile_router)
api_router.include_router(positions_router)
api_router.include_router(chat_router)
