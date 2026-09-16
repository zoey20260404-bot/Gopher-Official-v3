"""异步数据库会话基础设施。"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from gopher_agent.core.config import get_settings


class Base(DeclarativeBase):
    """所有 ORM model 的声明式基类。"""


settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """为单次请求提供数据库会话并确保释放连接。"""
    async with async_session_factory() as session:
        yield session
