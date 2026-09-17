"""稳定业务枚举测试。"""

from gopher_agent.domain.enums import (
    FavoriteCategory,
    MemoryScope,
    ReportStatus,
    SessionStatus,
    UserMode,
)


def test_v1_compatible_enum_values_are_stable() -> None:
    """外部契约使用的枚举值不得随内部命名变化。"""
    assert {item.value for item in UserMode} == {"beginner", "advanced"}
    assert {item.value for item in SessionStatus} == {"parsing", "confirming", "completed"}
    assert {item.value for item in ReportStatus} == {"processing", "completed", "failed"}
    assert {item.value for item in FavoriteCategory} == {"rush", "stable", "safe", "custom"}
    assert {item.value for item in MemoryScope} == {"session", "user", "agent"}
