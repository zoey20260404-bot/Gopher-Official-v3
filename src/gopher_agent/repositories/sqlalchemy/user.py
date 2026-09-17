"""用户 Repository 的 SQLAlchemy 实现。"""

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gopher_agent.models.user import User


class SqlAlchemyUserRepository:
    """在调用方提供的 session 中操作用户，不自行提交 transaction。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        """添加用户并 flush，使数据库生成的 ID 可见。"""
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        """按主键查询用户。"""
        return await self._session.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        """按唯一用户名查询用户。"""
        statement = select(User).where(User.username == username)
        return cast("User | None", await self._session.scalar(statement))
