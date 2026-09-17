"""异步数据库连接、会话和 transaction 基础设施。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from gopher_agent.core.config import get_settings


class Base(DeclarativeBase):
    """所有 ORM model 的声明式基类。"""


settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """为单次请求提供会话；提交动作由 Application Service 决定。"""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def transaction() -> AsyncIterator[AsyncSession]:
    """创建显式 transaction，异常时由 SQLAlchemy 自动回滚。"""
    async with async_session_factory() as session, session.begin():
        yield session


async def close_database() -> None:
    """释放 engine 维护的全部连接。"""
    await engine.dispose()
