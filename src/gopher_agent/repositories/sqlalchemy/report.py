"""选岗报告 SQLAlchemy Repository。"""

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gopher_agent.models.report import Report


class SqlAlchemyReportRepository:
    """在调用方 transaction 中维护报告，不自行 commit。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, report: Report) -> Report:
        """新增报告并 flush 数据库生成字段。"""
        self._session.add(report)
        await self._session.flush()
        return report

    async def get_owned(self, report_id: str, user_id: int) -> Report | None:
        """按归属读取报告，避免泄露其他用户资源。"""
        statement = select(Report).where(Report.report_id == report_id, Report.user_id == user_id)
        return cast("Report | None", await self._session.scalar(statement))

    async def get_owned_for_update(self, report_id: str, user_id: int) -> Report | None:
        """按归属加行锁读取报告。"""
        statement = (
            select(Report)
            .where(Report.report_id == report_id, Report.user_id == user_id)
            .with_for_update()
        )
        return cast("Report | None", await self._session.scalar(statement))
