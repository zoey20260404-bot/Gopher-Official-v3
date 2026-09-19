"""岗位 API schema 单元测试。"""

import pytest
from pydantic import ValidationError

from gopher_agent.api.schemas.positions import PositionSearchParams


def test_position_search_params_normalize_text_and_convert_query() -> None:
    params = PositionSearchParams(
        exam_type=" 国考 ",
        province="  ",
        keyword=" 税务 ",
        page=2,
        page_size=10,
    )

    query = params.to_query()

    assert query.exam_type == "国考"
    assert query.province is None
    assert query.keyword == "税务"
    assert query.page == 2
    assert query.page_size == 10


@pytest.mark.parametrize(
    ("field", "value"),
    [("page", 0), ("page_size", 0), ("page_size", 101), ("year", 1999)],
)
def test_position_search_params_reject_invalid_bounds(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        PositionSearchParams(**{field: value})
