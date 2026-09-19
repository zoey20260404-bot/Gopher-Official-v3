"""当前用户档案响应 schema。"""

from typing import Any

from pydantic import BaseModel


class ProfileResponse(BaseModel):
    """不存在档案记录时返回空 profile。"""

    user_id: int
    profile: dict[str, Any]
