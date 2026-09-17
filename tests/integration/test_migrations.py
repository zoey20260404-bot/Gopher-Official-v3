"""真实 PostgreSQL/pgvector migration 集成测试。"""

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from gopher_agent.core.config import get_settings

EXPECTED_TABLES = {
    "alembic_version",
    "favorites",
    "memories",
    "positions",
    "reports",
    "user_profiles",
    "user_sessions",
    "users",
}


async def inspect_database(database_url: str) -> tuple[set[str], bool]:
    """读取业务表和 vector extension 状态。"""
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            tables = await connection.run_sync(
                lambda sync_connection: set(inspect(sync_connection).get_table_names())
            )
            vector_enabled = bool(
                await connection.scalar(
                    text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
                )
            )
            return tables, vector_enabled
    finally:
        await engine.dispose()


@pytest.mark.db_integration
def test_migration_upgrade_downgrade_cycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """在显式指定的本地测试库验证完整 migration 周期。"""
    if os.getenv("RUN_DB_INTEGRATION") != "1":
        pytest.skip("设置 RUN_DB_INTEGRATION=1 后运行数据库集成测试")
    database_url = os.environ["TEST_DATABASE_URL"]
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()

    root = Path(__file__).resolve().parents[2]
    alembic_config = Config(root / "alembic.ini")

    command.upgrade(alembic_config, "head")
    tables, vector_enabled = asyncio.run(inspect_database(database_url))
    assert tables == EXPECTED_TABLES
    assert vector_enabled is True

    command.downgrade(alembic_config, "base")
    tables_after_downgrade, vector_still_enabled = asyncio.run(inspect_database(database_url))
    # Alembic 会保留自身的版本表，以便后续再次 upgrade。
    assert tables_after_downgrade == {"alembic_version"}
    assert vector_still_enabled is True

    # 测试结束时恢复到可开发状态。
    command.upgrade(alembic_config, "head")
