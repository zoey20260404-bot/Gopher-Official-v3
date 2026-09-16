"""健康检查接口。"""

from fastapi import APIRouter

from gopher_agent.api.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """返回进程存活状态；基础设施探针将在后续需求增加。"""
    return HealthResponse(status="ok")
