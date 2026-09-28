"""数据访问接口与实现。"""

from gopher_agent.repositories.protocols import (
    PositionMatchRepositoryProtocol,
    PositionRepositoryProtocol,
    UserRepositoryProtocol,
)
from gopher_agent.repositories.types import PositionCandidateQuery, PositionQuery

__all__ = [
    "PositionCandidateQuery",
    "PositionMatchRepositoryProtocol",
    "PositionQuery",
    "PositionRepositoryProtocol",
    "UserRepositoryProtocol",
]
