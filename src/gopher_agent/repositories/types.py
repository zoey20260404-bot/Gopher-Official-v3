"""Repository 输入类型。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PositionQuery:
    """本需求支持的最小岗位展示查询；硬条件匹配将在后续需求实现。"""

    exam_type: str | None = None
    year: int | None = None
    province: str | None = None
    city: str | None = None
    keyword: str | None = None
    page: int = 1
    page_size: int = 20

    @property
    def normalized_page(self) -> int:
        """将非法页码规范为第一页。"""
        return max(self.page, 1)

    @property
    def normalized_page_size(self) -> int:
        """限制单页数量，避免无界查询。"""
        return self.page_size if 1 <= self.page_size <= 100 else 20
