"""岗位资格三态规则引擎单元测试。"""

import pytest

from gopher_agent.domain.matching import MatchReason, PositionMatchStatus, RuleResult
from gopher_agent.domain.profile import ProfileData
from gopher_agent.services.matching import PositionEligibilityEvaluator
from gopher_agent.services.positions import PositionItem


def build_position(**overrides: object) -> PositionItem:
    """创建默认全部明确通过的岗位 DTO。"""
    values: dict[str, object] = {
        "id": 1,
        "exam_type": "国考",
        "year": 2026,
        "province": "广东",
        "city": "广州",
        "department": "税务局",
        "position_name": "行政执法员",
        "position_code": "001",
        "education_req": "不限",
        "major_req_exact": "不限",
        "major_req_category": "",
        "political_req": "不限",
        "fresh_graduate_req": None,
        "work_experience_years_req": 0,
        "gender_req": "不限",
        "age_limit": None,
        "household_registration_req": "不限",
        "other_restrictions": [],
        "remarks": "",
        "score_2025": None,
        "score_2024": None,
        "score_latest": None,
        "score_year": None,
        "applicant_ratio_2025": "",
    }
    values.update(overrides)
    return PositionItem(**values)  # type: ignore[arg-type]


def reason_for(profile: ProfileData, position: PositionItem, field: str) -> MatchReason:
    result = PositionEligibilityEvaluator().evaluate(profile, position)
    return next(reason for reason in result.reasons if reason.field == field)


def test_all_unlimited_rules_produce_eligible() -> None:
    result = PositionEligibilityEvaluator().evaluate(ProfileData(), build_position())

    assert result.status is PositionMatchStatus.ELIGIBLE
    assert {reason.result for reason in result.reasons} == {RuleResult.PASS}
    assert result.missing_profile_fields == ()


def test_explicit_failure_has_priority_over_manual_review_unknown() -> None:
    position = build_position(age_limit=35, remarks="需要人工检查")

    result = PositionEligibilityEvaluator().evaluate(ProfileData(age=40), position)

    assert result.status is PositionMatchStatus.INELIGIBLE
    assert reason_for(ProfileData(age=40), position, "age").result is RuleResult.FAIL
    assert reason_for(ProfileData(age=40), position, "remarks").result is RuleResult.UNKNOWN


@pytest.mark.parametrize(
    ("education", "requirement", "expected", "code"),
    [
        ("本科", "本科及以上", RuleResult.PASS, "education_level_satisfied"),
        ("硕士研究生", "仅限本科", RuleResult.FAIL, "education_level_not_satisfied"),
        ("大专", "本科及以上", RuleResult.FAIL, "education_level_not_satisfied"),
        ("本科", "本科及以下", RuleResult.PASS, "education_level_satisfied"),
        (None, "本科", RuleResult.UNKNOWN, "education_profile_missing"),
        ("本科", "", RuleResult.UNKNOWN, "education_requirement_missing"),
        ("本科", "本科或硕士研究生", RuleResult.UNKNOWN, "education_unrecognized"),
        ("其他学历", "本科", RuleResult.UNKNOWN, "education_unrecognized"),
    ],
)
def test_education_rule(
    education: str | None,
    requirement: str,
    expected: RuleResult,
    code: str,
) -> None:
    reason = reason_for(
        ProfileData(education=education),
        build_position(education_req=requirement),
        "education",
    )

    assert reason.result is expected
    assert reason.code == code


@pytest.mark.parametrize(
    ("major", "exact", "category", "expected", "code"),
    [
        ("计算机科学与技术", "法学、计算机科学与技术", "", RuleResult.PASS, "major_exact_match"),
        ("软件工程", "法学、计算机科学与技术", "", RuleResult.FAIL, "major_exact_mismatch"),
        (None, "法学、计算机科学与技术", "", RuleResult.UNKNOWN, "major_profile_missing"),
        (
            "计算机科学与技术",
            "",
            "计算机类",
            RuleResult.UNKNOWN,
            "major_category_mapping_unavailable",
        ),
        ("计算机科学与技术", "", "", RuleResult.UNKNOWN, "major_requirement_missing"),
        ("计算机", "计算机科学与技术", "", RuleResult.FAIL, "major_exact_mismatch"),
    ],
)
def test_major_rule_is_exact_and_conservative(
    major: str | None,
    exact: str,
    category: str,
    expected: RuleResult,
    code: str,
) -> None:
    reason = reason_for(
        ProfileData(major=major),
        build_position(major_req_exact=exact, major_req_category=category),
        "major",
    )

    assert reason.result is expected
    assert reason.code == code


@pytest.mark.parametrize(
    ("profile", "requirement", "field", "expected"),
    [
        (
            ProfileData(political_status="中共预备党员"),
            "中共党员(含预备党员)",
            "political_status",
            RuleResult.PASS,
        ),
        (
            ProfileData(political_status="群众"),
            "中共党员或共青团员",
            "political_status",
            RuleResult.FAIL,
        ),
        (
            ProfileData(political_status="未知面貌"),
            "中共党员",
            "political_status",
            RuleResult.UNKNOWN,
        ),
        (ProfileData(gender="女性"), "女", "gender", RuleResult.PASS),
        (ProfileData(gender="男"), "女", "gender", RuleResult.FAIL),
        (ProfileData(), "女", "gender", RuleResult.UNKNOWN),
    ],
)
def test_set_rules(
    profile: ProfileData,
    requirement: str,
    field: str,
    expected: RuleResult,
) -> None:
    position = (
        build_position(political_req=requirement)
        if field == "political_status"
        else build_position(gender_req=requirement)
    )

    assert reason_for(profile, position, field).result is expected


def test_boolean_and_numeric_rules_cover_pass_fail_and_missing() -> None:
    evaluator = PositionEligibilityEvaluator()
    position = build_position(
        fresh_graduate_req=True,
        work_experience_years_req=2,
        age_limit=35,
    )

    passed = evaluator.evaluate(
        ProfileData(fresh_graduate=True, work_experience_years=3, age=30), position
    )
    failed = evaluator.evaluate(
        ProfileData(fresh_graduate=False, work_experience_years=1, age=36), position
    )
    missing = evaluator.evaluate(ProfileData(), position)

    assert {
        item.result
        for item in passed.reasons
        if item.field in {"fresh_graduate", "work_experience_years", "age"}
    } == {RuleResult.PASS}
    assert {
        item.result
        for item in failed.reasons
        if item.field in {"fresh_graduate", "work_experience_years", "age"}
    } == {RuleResult.FAIL}
    assert set(missing.missing_profile_fields) >= {"fresh_graduate", "work_experience_years", "age"}


@pytest.mark.parametrize(
    ("household", "requirement", "expected", "code"),
    [
        ("广东省广州市", "广东省户籍", RuleResult.PASS, "household_satisfied"),
        ("广东省广州市", "广州市户籍", RuleResult.PASS, "household_satisfied"),
        ("广东省深圳市", "广州市户籍", RuleResult.FAIL, "household_city_mismatch"),
        ("浙江省杭州市", "广东省户籍", RuleResult.FAIL, "household_province_mismatch"),
        (None, "广东省户籍", RuleResult.UNKNOWN, "household_profile_missing"),
        ("广东", "本地户籍", RuleResult.UNKNOWN, "household_unrecognized"),
        ("广州市", "广东省户籍", RuleResult.UNKNOWN, "household_province_unknown"),
    ],
)
def test_household_rule(
    household: str | None,
    requirement: str,
    expected: RuleResult,
    code: str,
) -> None:
    reason = reason_for(
        ProfileData(household_registration=household),
        build_position(household_registration_req=requirement),
        "household_registration",
    )

    assert reason.result is expected
    assert reason.code == code


def test_free_text_restrictions_force_uncertain_without_profile_missing_fields() -> None:
    result = PositionEligibilityEvaluator().evaluate(
        ProfileData(),
        build_position(other_restrictions=["须通过体测"], remarks="咨询招录机关"),
    )

    assert result.status is PositionMatchStatus.UNCERTAIN
    assert "other_restrictions" not in result.missing_profile_fields
    assert "remarks" not in result.missing_profile_fields
