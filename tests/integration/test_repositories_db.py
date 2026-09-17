"""Repository 与 transaction 的真实 PostgreSQL 集成测试。"""

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from gopher_agent.models.position import Position
from gopher_agent.models.user import User
from gopher_agent.repositories.sqlalchemy.position import SqlAlchemyPositionRepository
from gopher_agent.repositories.sqlalchemy.user import SqlAlchemyUserRepository
from gopher_agent.repositories.types import PositionQuery

TEST_PASSWORD_HASH = "integration-test-value"  # noqa: S105 测试值，不是可用凭据


async def exercise_repositories(database_url: str) -> None:
    """在独立 event loop 中验证 Repository 与 transaction。"""
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    suffix = uuid4().hex
    username = f"feat002-{suffix}"
    rolled_back_username = f"feat002-rollback-{suffix}"
    position_code = f"P-{suffix}"

    try:
        async with session_factory() as session, session.begin():
            user = await SqlAlchemyUserRepository(session).add(
                User(username=username, password_hash=TEST_PASSWORD_HASH)
            )
            position = Position(
                exam_type="国考",
                year=2026,
                province="广东",
                city="广州",
                department="测试部门",
                position_name="测试岗位",
                position_code=position_code,
            )
            session.add(position)

        async with session_factory() as session:
            persisted_user = await SqlAlchemyUserRepository(session).get_by_username(username)
            positions, total = await SqlAlchemyPositionRepository(session).list(
                PositionQuery(year=2026, province="广东", keyword="测试岗位")
            )
            assert persisted_user is not None
            assert persisted_user.id == user.id
            assert total == 1
            assert positions[0].position_code == position_code

        with pytest.raises(RuntimeError, match="触发回滚"):
            async with session_factory() as session, session.begin():
                await SqlAlchemyUserRepository(session).add(
                    User(
                        username=rolled_back_username,
                        password_hash=TEST_PASSWORD_HASH,
                    )
                )
                raise RuntimeError("触发回滚")

        async with session_factory() as session:
            rolled_back_user = await SqlAlchemyUserRepository(session).get_by_username(
                rolled_back_username
            )
            assert rolled_back_user is None

        async with session_factory() as session, session.begin():
            await session.execute(delete(Position).where(Position.position_code == position_code))
            await session.execute(delete(User).where(User.username == username))
    finally:
        await engine.dispose()


@pytest.mark.db_integration
def test_repository_commit_query_and_rollback(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证 Repository 可持久化/查询，transaction 异常时不会留下数据。"""
    if os.getenv("RUN_DB_INTEGRATION") != "1":
        pytest.skip("设置 RUN_DB_INTEGRATION=1 后运行数据库集成测试")

    database_url = os.environ["TEST_DATABASE_URL"]
    monkeypatch.setenv("DATABASE_URL", database_url)
    root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(root / "alembic.ini")), "head")

    asyncio.run(exercise_repositories(database_url))
