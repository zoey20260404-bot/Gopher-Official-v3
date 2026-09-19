"""用户 Repository 的 SQLAlchemy 实现。"""

from typing import cast

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from gopher_agent.models.user import User, UserProfile
from gopher_agent.services.exceptions import UsernameAlreadyExistsError


class SqlAlchemyUserRepository:
    """在调用方提供的 session 中操作用户，不自行提交 transaction。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        """添加用户并 flush，使数据库生成的 ID 可见。"""
        self._session.add(user)
        try:
            await self._session.flush()
        except IntegrityError as error:
            # users 当前唯一业务冲突是用户名；数据库约束负责兜住并发注册竞争。
            raise UsernameAlreadyExistsError from error
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        """按主键查询用户。"""
        return await self._session.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        """按大小写不敏感的唯一用户名查询用户，兼容历史数据。"""
        statement = select(User).where(func.lower(User.username) == username.lower())
        return cast("User | None", await self._session.scalar(statement))

    async def get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        """按用户 ID 获取唯一权威档案。"""
        statement = select(UserProfile).where(UserProfile.user_id == user_id)
        return cast("UserProfile | None", await self._session.scalar(statement))
