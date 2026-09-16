"""健康检查数据模型。"""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: Literal["ok"]
