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
from gopher_agent.models.session import UserSession
from gopher_agent.models.user import User
from gopher_agent.repositories.sqlalchemy.position import SqlAlchemyPositionRepository
from gopher_agent.repositories.sqlalchemy.profile import SqlAlchemyProfileRepository
from gopher_agent.repositories.sqlalchemy.user import SqlAlchemyUserRepository
from gopher_agent.repositories.types import PositionCandidateQuery, PositionQuery
from gopher_agent.services.exceptions import UsernameAlreadyExistsError

TEST_PASSWORD_HASH = "integration-test-value"  # noqa: S105 测试值，不是可用凭据


async def exercise_repositories(database_url: str) -> None:
    """在独立 event loop 中验证 Repository 与 transaction。"""
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    suffix = uuid4().hex
    username = f"feat002-{suffix}"
    rolled_back_username = f"feat002-rollback-{suffix}"
    position_code = f"P-{suffix}"
    profile_session_id = str(uuid4())

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
            profile_repository = SqlAlchemyProfileRepository(session)
            profile_session = await profile_repository.add_session(
                UserSession(
                    session_id=profile_session_id,
                    user_id=user.id,
                    mode="advanced",
                    status="parsing",
                    profile_snapshot={},
                )
            )
            profile_session.status = "confirming"
            profile_session.profile_snapshot = {"education": "本科"}

        async with session_factory() as session, session.begin():
            profile_repository = SqlAlchemyProfileRepository(session)
            locked_profile_session = await profile_repository.get_owned_session_for_update(
                profile_session_id, user.id
            )
            assert locked_profile_session is not None
            locked_profile_session.status = "completed"
            await profile_repository.upsert_profile(
                user.id,
                {"education": "本科", "major": "计算机科学与技术"},
            )

        async with session_factory() as session:
            persisted_user = await SqlAlchemyUserRepository(session).get_by_username(
                username.upper()
            )
            positions, total = await SqlAlchemyPositionRepository(session).list(
                PositionQuery(year=2026, province="广东", keyword="测试岗位")
            )
            match_repository = SqlAlchemyPositionRepository(session)
            candidate_query = PositionCandidateQuery(year=2026, province="广东")
            candidate_total = await match_repository.count_candidates(candidate_query)
            candidates = await match_repository.list_candidates(candidate_query, limit=10)
            assert persisted_user is not None
            assert persisted_user.id == user.id
            persisted_profile = await SqlAlchemyUserRepository(session).get_profile_by_user_id(
                user.id
            )
            assert persisted_profile is not None
            assert persisted_profile.profile["major"] == "计算机科学与技术"
            assert total == 1
            assert positions[0].position_code == position_code
            assert candidate_total == 1
            assert candidates[0].position_code == position_code

        with pytest.raises(UsernameAlreadyExistsError):
            async with session_factory() as session, session.begin():
                await SqlAlchemyUserRepository(session).add(
                    User(username=username.upper(), password_hash=TEST_PASSWORD_HASH)
                )

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
