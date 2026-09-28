"""岗位 Repository 的 SQLAlchemy 实现。"""

import builtins

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from gopher_agent.models.position import Position
from gopher_agent.repositories.types import PositionCandidateQuery, PositionQuery


def build_position_statement(
    query: PositionQuery | PositionCandidateQuery,
) -> Select[tuple[Position]]:
    """构建参数化岗位查询，便于独立验证过滤语义。"""
    statement = select(Position)
    if query.exam_type:
        statement = statement.where(Position.exam_type == query.exam_type)
    if query.year is not None:
        statement = statement.where(Position.year == query.year)
    if query.province:
        statement = statement.where(
            or_(Position.province == query.province, Position.province == "国家")
        )
    if query.city:
        statement = statement.where(Position.city.ilike(f"%{query.city}%"))
    if query.keyword:
        pattern = f"%{query.keyword}%"
        statement = statement.where(
            or_(Position.position_name.ilike(pattern), Position.department.ilike(pattern))
        )
    return statement


class SqlAlchemyPositionRepository:
    """岗位分页查询实现。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, query: PositionQuery) -> tuple[list[Position], int]:
        """执行同一组过滤条件的计数与分页查询。"""
        filtered = build_position_statement(query)
        count_statement = select(func.count()).select_from(filtered.order_by(None).subquery())
        total = await self._session.scalar(count_statement)

        page_statement = (
            filtered.order_by(Position.year.desc(), Position.id.desc())
            .offset((query.normalized_page - 1) * query.normalized_page_size)
            .limit(query.normalized_page_size)
        )
        rows = await self._session.scalars(page_statement)
        return list(rows.all()), int(total or 0)

    async def count_candidates(self, query: PositionCandidateQuery) -> int:
        """对粗筛条件计数，供 Service 在读取前执行上限保护。"""
        filtered = build_position_statement(query)
        statement = select(func.count()).select_from(filtered.order_by(None).subquery())
        total = await self._session.scalar(statement)
        return int(total or 0)

    async def list_candidates(
        self, query: PositionCandidateQuery, *, limit: int
    ) -> builtins.list[Position]:
        """读取至多 limit + 1 条候选，防止计数与读取之间的数据竞争造成截断。"""
        statement = (
            build_position_statement(query)
            .order_by(Position.year.desc(), Position.id.desc())
            .limit(limit + 1)
        )
        rows = await self._session.scalars(statement)
        return list(rows.all())
