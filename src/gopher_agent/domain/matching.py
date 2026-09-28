"""岗位资格匹配的稳定领域类型。"""

from dataclasses import dataclass
from enum import StrEnum


class RuleResult(StrEnum):
    """单项硬条件判断结果。"""

    PASS = "pass"  # noqa: S105 规则结果值，不是凭据
    FAIL = "fail"
    UNKNOWN = "unknown"


class PositionMatchStatus(StrEnum):
    """一个岗位的聚合资格判断。"""

    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNCERTAIN = "uncertain"


class PositionMatchFilter(StrEnum):
    """岗位匹配列表的状态过滤方式。"""

    POTENTIAL = "potential"
    ELIGIBLE = "eligible"
    UNCERTAIN = "uncertain"
    INELIGIBLE = "ineligible"
    ALL = "all"


type ReasonValue = str | int | bool | None


@dataclass(frozen=True, slots=True)
class MatchReason:
    """一项可供用户验证的确定性判断依据。"""

    field: str
    result: RuleResult
    code: str
    message: str
    profile_value: ReasonValue
    requirement: ReasonValue


@dataclass(frozen=True, slots=True)
class PositionEligibility:
    """rule engine 对单个岗位的聚合结果。"""

    status: PositionMatchStatus
    reasons: tuple[MatchReason, ...]
    missing_profile_fields: tuple[str, ...]
