"""跨数据层和业务层共享的稳定枚举。"""

from enum import StrEnum


class UserMode(StrEnum):
    """用户内容表达模式。"""

    BEGINNER = "beginner"
    ADVANCED = "advanced"


class SessionStatus(StrEnum):
    """用户会话状态。"""

    PARSING = "parsing"
    CONFIRMING = "confirming"
    COMPLETED = "completed"


class ReportStatus(StrEnum):
    """选岗报告生成状态。"""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FavoriteCategory(StrEnum):
    """收藏岗位分类。"""

    RUSH = "rush"
    STABLE = "stable"
    SAFE = "safe"
    CUSTOM = "custom"


class MemoryScope(StrEnum):
    """长期记忆的访问作用域。"""

    SESSION = "session"
    USER = "user"
    AGENT = "agent"
