"""数据库基础设施单元测试。"""

from gopher_agent.core.database import Base, engine


async def test_database_uses_postgresql_without_eager_connection() -> None:
    """初始化 engine 时不应立即依赖本地 PostgreSQL 可用。"""
    assert engine.dialect.name == "postgresql"
    assert not Base.metadata.tables

    await engine.dispose()
