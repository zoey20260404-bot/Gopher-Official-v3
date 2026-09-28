"""数据访问抽象，业务层只依赖这些 Protocol。"""

from typing import Protocol

from gopher_agent.models.position import Position
from gopher_agent.models.report import Report
from gopher_agent.models.session import UserSession
from gopher_agent.models.user import User, UserProfile
from gopher_agent.repositories.types import PositionCandidateQuery, PositionQuery


class UserRepositoryProtocol(Protocol):
    """用户数据访问契约。"""

    async def add(self, user: User) -> User:
        """新增用户并 flush 生成字段。"""
        ...

    async def get_by_id(self, user_id: int) -> User | None:
        """按主键获取用户。"""
        ...

    async def get_by_username(self, username: str) -> User | None:
        """按唯一用户名获取用户。"""
        ...

    async def get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        """获取用户唯一的权威档案。"""
        ...


class PositionRepositoryProtocol(Protocol):
    """岗位数据访问契约。"""

    async def list(self, query: PositionQuery) -> tuple[list[Position], int]:
        """返回当前页岗位和过滤后的总数。"""
        ...


class PositionMatchRepositoryProtocol(Protocol):
    """资格匹配所需的有界候选岗位数据访问契约。"""

    async def count_candidates(self, query: PositionCandidateQuery) -> int:
        """返回资格匹配粗筛后的候选岗位数。"""
        ...

    async def list_candidates(self, query: PositionCandidateQuery, *, limit: int) -> list[Position]:
        """按稳定顺序返回有界候选集，并额外读取一条用于防御截断。"""
        ...


class ProfileRepositoryProtocol(Protocol):
    """档案解析 session 与权威档案的 transaction 内数据访问契约。"""

    async def add_session(self, user_session: UserSession) -> UserSession:
        """新增解析 session 并 flush。"""
        ...

    async def get_owned_session_for_update(
        self, session_id: str, user_id: int
    ) -> UserSession | None:
        """加锁读取属于指定用户的解析 session。"""
        ...

    async def get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        """读取用户当前的权威档案，供新访谈初始化快照。"""
        ...

    async def upsert_profile(self, user_id: int, profile: dict[str, object]) -> UserProfile:
        """按 user_id 新增或更新唯一权威档案。"""
        ...


class ReportRepositoryProtocol(Protocol):
    """选岗报告业务状态的数据访问契约。"""

    async def add(self, report: Report) -> Report:
        """新增报告并 flush。"""
        ...

    async def get_owned(self, report_id: str, user_id: int) -> Report | None:
        """读取属于指定用户的报告。"""
        ...

    async def get_owned_for_update(self, report_id: str, user_id: int) -> Report | None:
        """加锁读取属于指定用户的报告。"""
        ...
