"""SQLAlchemy Repository 单元测试。"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from gopher_agent.models.position import Position
from gopher_agent.models.user import User
from gopher_agent.repositories.sqlalchemy.position import (
    SqlAlchemyPositionRepository,
    build_position_statement,
)
from gopher_agent.repositories.sqlalchemy.user import SqlAlchemyUserRepository
from gopher_agent.repositories.types import PositionQuery
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
