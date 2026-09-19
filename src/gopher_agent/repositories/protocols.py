"""数据访问抽象，业务层只依赖这些 Protocol。"""

from typing import Protocol

from gopher_agent.models.position import Position
from gopher_agent.models.user import User, UserProfile
from gopher_agent.repositories.types import PositionQuery


class UserRepositoryProtocol(Protocol):
    """用户数据访问契约。"""

    async def add(self, user: User) -> User:
        """新增用户并 flush 生成字段。"""
        ...

    async def get_by_id(self, user_id: int) -> User | None:
        """按主键获取用户。"""
        ...

    async def get_by_username(self, username: str) -> User | None:
        """按唯一用户名获取用户。"""
        ...

    async def get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        """获取用户唯一的权威档案。"""
        ...


class PositionRepositoryProtocol(Protocol):
    """岗位数据访问契约。"""

    async def list(self, query: PositionQuery) -> tuple[list[Position], int]:
        """返回当前页岗位和过滤后的总数。"""
        ...
