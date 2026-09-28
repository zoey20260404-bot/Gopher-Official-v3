"""档案解析 session 与权威档案 SQLAlchemy Repository。"""

from typing import cast

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from gopher_agent.models.session import UserSession
from gopher_agent.models.user import UserProfile


class SqlAlchemyProfileRepository:
    """在调用方 transaction 中保存档案数据，不自行 commit。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_session(self, user_session: UserSession) -> UserSession:
        """添加解析 session 并 flush，使数据库生成字段可见。"""
        self._session.add(user_session)
        await self._session.flush()
        return user_session

    async def get_owned_session_for_update(
        self, session_id: str, user_id: int
    ) -> UserSession | None:
        """按不泄露其他用户数据的复合条件加行锁查询。"""
        statement = (
            select(UserSession)
            .where(UserSession.session_id == session_id, UserSession.user_id == user_id)
            .with_for_update()
        )
        return cast("UserSession | None", await self._session.scalar(statement))

    async def upsert_profile(self, user_id: int, profile: dict[str, object]) -> UserProfile:
        """使用 PostgreSQL 原子 upsert 消除并发首次确认竞争。"""
        statement = (
            insert(UserProfile)
            .values(user_id=user_id, profile=profile)
            .on_conflict_do_update(
                index_elements=[UserProfile.user_id],
                set_={"profile": profile, "updated_at": func.now()},
            )
            .returning(UserProfile)
        )
        result = await self._session.scalar(statement)
        if result is None:  # pragma: no cover - PostgreSQL RETURNING 的防御性保护
            raise RuntimeError("权威档案 upsert 未返回记录")
        return result
