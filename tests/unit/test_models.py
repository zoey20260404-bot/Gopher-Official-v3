"""ORM metadata 与 PostgreSQL DDL 单元测试。"""

from pgvector.sqlalchemy import Vector
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import CreateTable

import gopher_agent.models  # noqa: F401 注册所有 model
from gopher_agent.core.database import Base

EXPECTED_TABLES = {
    "favorites",
    "memories",
    "positions",
    "reports",
    "user_profiles",
    "user_sessions",
    "users",
}


def test_all_business_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_structured_fields_use_native_postgresql_types() -> None:
    assert isinstance(Base.metadata.tables["user_profiles"].c.profile.type, JSONB)
    assert isinstance(Base.metadata.tables["reports"].c.result.type, JSONB)

    embedding_type = Base.metadata.tables["memories"].c.embedding.type
    assert isinstance(embedding_type, Vector)
    assert embedding_type.dim == 1024


def test_every_model_compiles_for_postgresql() -> None:
    dialect = postgresql.dialect()  # type: ignore[no-untyped-call]

    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=dialect))
        assert f"CREATE TABLE {table.name}" in ddl


def test_critical_unique_constraints_are_present() -> None:
    favorites = Base.metadata.tables["favorites"]
    positions = Base.metadata.tables["positions"]

    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"user_id", "position_id"}
        for constraint in favorites.constraints
    )
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == {"year", "position_code"}
        for constraint in positions.constraints
    )
