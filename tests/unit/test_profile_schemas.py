"""用户档案 Pydantic schema 单元测试。"""

import pytest
from pydantic import TypeAdapter, ValidationError

from gopher_agent.api.schemas.profile import (
    AdvancedParseRequest,
    AnswerProfileInterviewRequest,
    BeginnerParseRequest,
    ParseRequest,
)
from gopher_agent.domain.profile import ProfileData


def test_profile_normalizes_strings_and_lists_missing_fields_in_order() -> None:
    profile = ProfileData(education="  本科  ", major="   ", age=24)

    assert profile.education == "本科"
    assert profile.major is None
    assert profile.missing_fields[:3] == ["major", "political_status", "fresh_graduate"]
    assert "education" not in profile.missing_fields
    assert "age" not in profile.missing_fields


@pytest.mark.parametrize(
    ("field", "value"),
    [("age", 15), ("age", 101), ("work_experience_years", -1)],
)
def test_profile_rejects_invalid_numeric_boundaries(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        ProfileData.model_validate({field: value})


def test_parse_request_discriminates_modes_and_forbids_cross_mode_fields() -> None:
    adapter: TypeAdapter[BeginnerParseRequest | AdvancedParseRequest] = TypeAdapter(ParseRequest)

    beginner = adapter.validate_python({"mode": "beginner", "content": "  本科学历  "})
    advanced = adapter.validate_python({"mode": "advanced", "profile": {"age": 24}})

    assert isinstance(beginner, BeginnerParseRequest)
    assert beginner.content == "本科学历"
    assert isinstance(advanced, AdvancedParseRequest)
    assert advanced.profile.age == 24
    with pytest.raises(ValidationError):
        adapter.validate_python({"mode": "beginner", "content": "本科", "profile": {"age": 24}})
    with pytest.raises(ValidationError):
        adapter.validate_python({"mode": "beginner", "content": "   "})


def test_interview_answer_requires_exactly_one_answer_mode() -> None:
    identifiers = {
        "session_id": "0199d418-9f9a-7000-8000-000000000001",
        "question_id": "0199d418-9f9a-7000-8000-000000000002",
        "request_id": "0199d418-9f9a-7000-8000-000000000003",
    }

    answered = AnswerProfileInterviewRequest(**identifiers, answer="  本科  ")
    skipped = AnswerProfileInterviewRequest(**identifiers, skip=True)

    assert answered.answer == "本科"
    assert skipped.answer is None
    with pytest.raises(ValidationError):
        AnswerProfileInterviewRequest(**identifiers)
    with pytest.raises(ValidationError):
        AnswerProfileInterviewRequest(**identifiers, answer="本科", skip=True)
