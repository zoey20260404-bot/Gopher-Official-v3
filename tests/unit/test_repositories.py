"""SQLAlchemy Repository 单元测试。"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from gopher_agent.models.position import Position
from gopher_agent.models.session import UserSession
from gopher_agent.models.user import User
from gopher_agent.repositories.sqlalchemy.position import (
    SqlAlchemyPositionRepository,
    build_position_statement,
)
from gopher_agent.repositories.sqlalchemy.profile import SqlAlchemyProfileRepository
from gopher_agent.repositories.sqlalchemy.user import SqlAlchemyUserRepository
from gopher_agent.repositories.types import PositionCandidateQuery, PositionQuery
from gopher_agent.services.exceptions import UsernameAlreadyExistsError


async def test_user_repository_flushes_without_committing() -> None:
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock()
    user = User()
    user.username = "zoey"
    user.password_hash = "test-value"  # noqa: S105 测试数据，不是可用凭据

    result = await SqlAlchemyUserRepository(session).add(user)

    assert result is user
    session.add.assert_called_once_with(user)
    session.flush.assert_awaited_once_with()
    session.commit.assert_not_called()


async def test_user_repository_translates_insert_conflict() -> None:
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock(side_effect=IntegrityError("insert", {}, Exception("duplicate")))
    user = User(username="zoey", password_hash="test-value")  # noqa: S106

    with pytest.raises(UsernameAlreadyExistsError):
        await SqlAlchemyUserRepository(session).add(user)


async def test_user_repository_queries_by_username() -> None:
    session = MagicMock(spec=AsyncSession)
    expected = User()
    expected.username = "zoey"
    expected.password_hash = "test-value"  # noqa: S105 测试数据，不是可用凭据
    session.scalar = AsyncMock(return_value=expected)

    result = await SqlAlchemyUserRepository(session).get_by_username("ZoEy")

    assert result is expected
    statement = session.scalar.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert "lower(users.username)" in str(compiled)
    assert "zoey" in compiled.params.values()


async def test_user_repository_queries_profile_by_user_id() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=None)

    result = await SqlAlchemyUserRepository(session).get_profile_by_user_id(42)

    assert result is None
    statement = session.scalar.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert "user_profiles.user_id" in str(compiled)
    assert 42 in compiled.params.values()


async def test_profile_repository_adds_session_without_committing() -> None:
    session = MagicMock(spec=AsyncSession)
    session.flush = AsyncMock()
    user_session = UserSession(
        session_id="session-1",
        user_id=7,
        mode="advanced",
        status="parsing",
        profile_snapshot={},
    )

    result = await SqlAlchemyProfileRepository(session).add_session(user_session)

    assert result is user_session
    session.add.assert_called_once_with(user_session)
    session.flush.assert_awaited_once_with()
    session.commit.assert_not_called()


async def test_profile_repository_locks_owned_session() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=None)

    result = await SqlAlchemyProfileRepository(session).get_owned_session_for_update("session-1", 7)

    assert result is None
    statement = session.scalar.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert "FOR UPDATE" in str(compiled)
    assert "session-1" in compiled.params.values()
    assert 7 in compiled.params.values()


async def test_profile_repository_uses_atomic_postgresql_upsert() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=MagicMock())

    await SqlAlchemyProfileRepository(session).upsert_profile(7, {"education": "本科"})

    statement = session.scalar.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    sql = str(compiled)
    assert "ON CONFLICT (user_id) DO UPDATE" in sql
    assert "RETURNING user_profiles" in sql
    session.commit.assert_not_called()


def test_position_query_is_parameterized_and_bounded() -> None:
    query = PositionQuery(
        exam_type="国考",
        year=2026,
        province="广东",
        city="广州",
        keyword="税务",
        page=-1,
        page_size=1000,
    )
    dialect = postgresql.dialect()  # type: ignore[no-untyped-call]
    compiled = build_position_statement(query).compile(dialect=dialect)

    assert query.normalized_page == 1
    assert query.normalized_page_size == 20
    assert "国考" in compiled.params.values()
    assert "广东" in compiled.params.values()
    assert "国家" in compiled.params.values()
    assert "%广州%" in compiled.params.values()
    assert "%税务%" in compiled.params.values()
    assert "国考" not in str(compiled)


async def test_position_repository_returns_page_and_total() -> None:
    session = MagicMock(spec=AsyncSession)
    position = Position()
    position.exam_type = "国考"
    position.year = 2026
    position.province = "国家"
    position.department = "税务局"
    position.position_name = "一级行政执法员"
    position.position_code = "001"
    scalar_rows = MagicMock()
    scalar_rows.all.return_value = [position]
    session.scalar = AsyncMock(return_value=1)
    session.scalars = AsyncMock(return_value=scalar_rows)

    rows, total = await SqlAlchemyPositionRepository(session).list(PositionQuery())

    assert rows == [position]
    assert total == 1
    session.scalar.assert_awaited_once()
    session.scalars.assert_awaited_once()
    page_statement = session.scalars.await_args.args[0]
    compiled = str(page_statement.compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]
    assert "ORDER BY positions.year DESC, positions.id DESC" in compiled


async def test_position_repository_counts_and_bounds_match_candidates() -> None:
    session = MagicMock(spec=AsyncSession)
    session.scalar = AsyncMock(return_value=3)
    scalar_rows = MagicMock()
    scalar_rows.all.return_value = []
    session.scalars = AsyncMock(return_value=scalar_rows)
    repository = SqlAlchemyPositionRepository(session)
    query = PositionCandidateQuery(exam_type="国考", province="广东")

    total = await repository.count_candidates(query)
    candidates = await repository.list_candidates(query, limit=2)

    assert total == 3
    assert candidates == []
    count_statement = session.scalar.await_args.args[0]
    count_sql = str(count_statement.compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]
    assert "count" in count_sql.lower()
    candidate_statement = session.scalars.await_args.args[0]
    compiled = candidate_statement.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert "ORDER BY positions.year DESC, positions.id DESC" in str(compiled)
    assert 3 in compiled.params.values()
