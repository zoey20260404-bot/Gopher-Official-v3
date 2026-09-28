"""确定性岗位资格规则与匹配 Application Service。"""

import re
import unicodedata
from dataclasses import dataclass, replace

from gopher_agent.domain.matching import (
    MatchReason,
    PositionEligibility,
    PositionMatchFilter,
    PositionMatchStatus,
    ReasonValue,
    RuleResult,
)
from gopher_agent.domain.profile import ProfileData
from gopher_agent.repositories.protocols import (
    PositionMatchRepositoryProtocol,
    UserRepositoryProtocol,
)
from gopher_agent.repositories.types import PositionCandidateQuery
from gopher_agent.services.exceptions import (
    PositionCandidateLimitExceededError,
    UserProfileNotConfirmedError,
)
from gopher_agent.services.positions import PositionItem

_UNLIMITED_VALUES = {"不限", "无要求", "不限制"}
_SPLIT_PATTERN = re.compile(r"[、,;/\n]+|或者|或")
_EDUCATION_LEVELS = {
    "高中": 0,
    "中专": 0,
    "大专": 1,
    "专科": 1,
    "本科": 2,
    "硕士研究生": 3,
    "硕士": 3,
    "博士研究生": 4,
    "博士": 4,
}
_POLITICAL_ALIASES = {
    "中共党员": "中共党员",
    "中国共产党党员": "中共党员",
    "中共预备党员": "中共预备党员",
    "中国共产党预备党员": "中共预备党员",
    "共青团员": "共青团员",
    "群众": "群众",
    "民主党派": "民主党派",
    "无党派人士": "无党派人士",
}
_GENDER_ALIASES = {"男": "男", "男性": "男", "女": "女", "女性": "女"}
_PROVINCES = (
    "内蒙古",
    "黑龙江",
    "新疆",
    "广西",
    "宁夏",
    "西藏",
    "香港",
    "澳门",
    "北京",
    "天津",
    "上海",
    "重庆",
    "河北",
    "山西",
    "辽宁",
    "吉林",
    "江苏",
    "浙江",
    "安徽",
    "福建",
    "江西",
    "山东",
    "河南",
    "湖北",
    "湖南",
    "广东",
    "海南",
    "四川",
    "贵州",
    "云南",
    "陕西",
    "甘肃",
    "青海",
    "台湾",
)
_MUNICIPALITIES = {"北京", "天津", "上海", "重庆"}
_PROFILE_FIELDS = frozenset(ProfileData.model_fields)


def _normalize(value: str) -> str:
    """执行不会引入语义猜测的文本规范化。"""
    return "".join(unicodedata.normalize("NFKC", value).strip().split()).casefold()


def _is_unlimited(value: str) -> bool:
    return _normalize(value) in _UNLIMITED_VALUES


def _reason(
    field: str,
    result: RuleResult,
    code: str,
    message: str,
    profile_value: ReasonValue,
    requirement: ReasonValue,
) -> MatchReason:
    return MatchReason(field, result, code, message, profile_value, requirement)


class PositionEligibilityEvaluator:
    """对单个岗位执行无 I/O、可复现的三态硬条件判断。"""

    def evaluate(self, profile: ProfileData, position: PositionItem) -> PositionEligibility:
        """执行全部规则，并以 fail 优先于 unknown 的顺序聚合。"""
        reasons = (
            self._education(profile.education, position.education_req),
            self._major(profile.major, position.major_req_exact, position.major_req_category),
            self._political(profile.political_status, position.political_req),
            self._fresh_graduate(profile.fresh_graduate, position.fresh_graduate_req),
            self._work_experience(
                profile.work_experience_years, position.work_experience_years_req
            ),
            self._gender(profile.gender, position.gender_req),
            self._age(profile.age, position.age_limit),
            self._household(profile.household_registration, position.household_registration_req),
            self._other_restrictions(position.other_restrictions),
            self._remarks(position.remarks),
        )
        if any(reason.result is RuleResult.FAIL for reason in reasons):
            status = PositionMatchStatus.INELIGIBLE
        elif any(reason.result is RuleResult.UNKNOWN for reason in reasons):
            status = PositionMatchStatus.UNCERTAIN
        else:
            status = PositionMatchStatus.ELIGIBLE

        missing = tuple(
            dict.fromkeys(
                reason.field
                for reason in reasons
                if reason.result is RuleResult.UNKNOWN
                and reason.field in _PROFILE_FIELDS
                and reason.profile_value is None
            )
        )
        return PositionEligibility(status=status, reasons=reasons, missing_profile_fields=missing)

    @staticmethod
    def _education(profile_value: str | None, requirement: str) -> MatchReason:
        field = "education"
        if _is_unlimited(requirement):
            return _reason(
                field,
                RuleResult.PASS,
                "education_unlimited",
                "岗位学历不限",
                profile_value,
                requirement,
            )
        if not requirement.strip():
            return _reason(
                field,
                RuleResult.UNKNOWN,
                "education_requirement_missing",
                "岗位学历要求缺失",
                profile_value,
                requirement,
            )
        if profile_value is None:
            return _reason(
                field,
                RuleResult.UNKNOWN,
                "education_profile_missing",
                "用户学历未填写",
                None,
                requirement,
            )

        user_levels = _extract_education_levels(profile_value)
        required_levels = _extract_education_levels(requirement)
        if len(user_levels) != 1 or len(required_levels) != 1:
            return _reason(
                field,
                RuleResult.UNKNOWN,
                "education_unrecognized",
                "学历信息无法可靠规范化",
                profile_value,
                requirement,
            )
        user_level = next(iter(user_levels))
        required_level = next(iter(required_levels))
        normalized = _normalize(requirement)
        if "及以上" in normalized or ("以上" in normalized and "仅限" not in normalized):
            passed = user_level >= required_level
        elif "及以下" in normalized or ("以下" in normalized and "仅限" not in normalized):
            passed = user_level <= required_level
        else:
            passed = user_level == required_level
        return _reason(
            field,
            RuleResult.PASS if passed else RuleResult.FAIL,
            "education_level_satisfied" if passed else "education_level_not_satisfied",
            "用户学历满足岗位要求" if passed else "用户学历不满足岗位要求",
            profile_value,
            requirement,
        )

    @staticmethod
    def _major(
        profile_value: str | None, exact_requirement: str, category_requirement: str
    ) -> MatchReason:
        field = "major"
        if _is_unlimited(exact_requirement):
            return _reason(
                field,
                RuleResult.PASS,
                "major_unlimited",
                "岗位专业不限",
                profile_value,
                exact_requirement or category_requirement,
            )
        if exact_requirement.strip():
            if profile_value is None:
                return _reason(
                    field,
                    RuleResult.UNKNOWN,
                    "major_profile_missing",
                    "用户专业未填写",
                    None,
                    exact_requirement,
                )
            allowed = {_normalize(token) for token in _split_values(exact_requirement)}
            if not allowed:
                return _reason(
                    field,
                    RuleResult.UNKNOWN,
                    "major_requirement_unrecognized",
                    "岗位专业要求无法可靠拆分",
                    profile_value,
                    exact_requirement,
                )
            passed = _normalize(profile_value) in allowed
            return _reason(
                field,
                RuleResult.PASS if passed else RuleResult.FAIL,
                "major_exact_match" if passed else "major_exact_mismatch",
                "用户专业命中岗位明确专业列表" if passed else "用户专业未命中岗位明确专业列表",
                profile_value,
                exact_requirement,
            )
        if _is_unlimited(category_requirement):
            return _reason(
                field,
                RuleResult.PASS,
                "major_unlimited",
                "岗位专业不限",
                profile_value,
                category_requirement,
            )
        if category_requirement.strip():
            return _reason(
                field,
                RuleResult.UNKNOWN,
                "major_category_mapping_unavailable",
                "缺少可靠的专业大类映射",
                profile_value,
                category_requirement,
            )
        return _reason(
            field,
            RuleResult.UNKNOWN,
            "major_requirement_missing",
            "岗位专业要求缺失",
            profile_value,
            None,
        )

    @staticmethod
    def _political(profile_value: str | None, requirement: str) -> MatchReason:
        return _set_rule(
            field="political_status",
            profile_value=profile_value,
            requirement=requirement,
            aliases=_POLITICAL_ALIASES,
            special_allowed={
                "中共党员(含预备党员)": {"中共党员", "中共预备党员"},
                "中共党员含预备党员": {"中共党员", "中共预备党员"},
            },
        )

    @staticmethod
    def _fresh_graduate(profile_value: bool | None, requirement: bool | None) -> MatchReason:
        field = "fresh_graduate"
        if requirement is None:
            return _reason(
                field,
                RuleResult.PASS,
                "fresh_graduate_unlimited",
                "岗位不限应届生身份",
                profile_value,
                None,
            )
        if profile_value is None:
            return _reason(
                field,
                RuleResult.UNKNOWN,
                "fresh_graduate_profile_missing",
                "用户应届生身份未填写",
                None,
                requirement,
            )
        passed = profile_value is requirement
        return _reason(
            field,
            RuleResult.PASS if passed else RuleResult.FAIL,
            "fresh_graduate_satisfied" if passed else "fresh_graduate_not_satisfied",
            "用户应届生身份满足岗位要求" if passed else "用户应届生身份不满足岗位要求",
            profile_value,
            requirement,
        )

    @staticmethod
    def _work_experience(profile_value: int | None, requirement: int) -> MatchReason:
        field = "work_experience_years"
        if requirement <= 0:
            return _reason(
                field,
                RuleResult.PASS,
                "work_experience_unlimited",
                "岗位无工作年限要求",
                profile_value,
                requirement,
            )
        if profile_value is None:
            return _reason(
                field,
                RuleResult.UNKNOWN,
                "work_experience_profile_missing",
                "用户工作年限未填写",
                None,
                requirement,
            )
        passed = profile_value >= requirement
        return _reason(
            field,
            RuleResult.PASS if passed else RuleResult.FAIL,
            "work_experience_satisfied" if passed else "work_experience_not_satisfied",
            "用户工作年限满足岗位要求" if passed else "用户工作年限不满足岗位要求",
            profile_value,
            requirement,
        )

    @staticmethod
    def _gender(profile_value: str | None, requirement: str) -> MatchReason:
        return _set_rule(
            field="gender",
            profile_value=profile_value,
            requirement=requirement,
            aliases=_GENDER_ALIASES,
        )

    @staticmethod
    def _age(profile_value: int | None, requirement: int | None) -> MatchReason:
        field = "age"
        if requirement is None:
            return _reason(
                field, RuleResult.PASS, "age_unlimited", "岗位无年龄上限", profile_value, None
            )
        if profile_value is None:
            return _reason(
                field,
                RuleResult.UNKNOWN,
                "age_profile_missing",
                "用户年龄未填写",
                None,
                requirement,
            )
        passed = profile_value <= requirement
        return _reason(
            field,
            RuleResult.PASS if passed else RuleResult.FAIL,
            "age_satisfied" if passed else "age_not_satisfied",
            "用户年龄满足岗位要求" if passed else "用户年龄超过岗位上限",
            profile_value,
            requirement,
        )

    @staticmethod
    def _household(profile_value: str | None, requirement: str) -> MatchReason:
        field = "household_registration"
        if _is_unlimited(requirement):
            return _reason(
                field,
                RuleResult.PASS,
                "household_unlimited",
                "岗位户籍不限",
                profile_value,
                requirement,
            )
        if not requirement.strip():
            return _reason(
                field,
                RuleResult.UNKNOWN,
                "household_requirement_missing",
                "岗位户籍要求缺失",
                profile_value,
                requirement,
            )
        if profile_value is None:
            return _reason(
                field,
                RuleResult.UNKNOWN,
                "household_profile_missing",
                "用户户籍未填写",
                None,
                requirement,
            )
        user_location = _parse_location(profile_value)
        required_location = _parse_location(requirement)
        if required_location == (None, None) or user_location == (None, None):
            return _reason(
                field,
                RuleResult.UNKNOWN,
                "household_unrecognized",
                "户籍信息无法可靠规范化",
                profile_value,
                requirement,
            )
        user_province, user_city = user_location
        required_province, required_city = required_location
        if required_province is not None:
            if user_province is None:
                return _reason(
                    field,
                    RuleResult.UNKNOWN,
                    "household_province_unknown",
                    "无法确定用户所属省份",
                    profile_value,
                    requirement,
                )
            if user_province != required_province:
                return _reason(
                    field,
                    RuleResult.FAIL,
                    "household_province_mismatch",
                    "用户户籍不满足岗位省级要求",
                    profile_value,
                    requirement,
                )
        if required_city is not None:
            if user_city is None:
                return _reason(
                    field,
                    RuleResult.UNKNOWN,
                    "household_city_unknown",
                    "无法确定用户所属城市",
                    profile_value,
                    requirement,
                )
            if user_city != required_city:
                return _reason(
                    field,
                    RuleResult.FAIL,
                    "household_city_mismatch",
                    "用户户籍不满足岗位市级要求",
                    profile_value,
                    requirement,
                )
        return _reason(
            field,
            RuleResult.PASS,
            "household_satisfied",
            "用户户籍满足岗位要求",
            profile_value,
            requirement,
        )

    @staticmethod
    def _other_restrictions(requirements: list[object]) -> MatchReason:
        if requirements:
            return _reason(
                "other_restrictions",
                RuleResult.UNKNOWN,
                "other_restrictions_manual_review",
                "岗位存在其他限制, 需要人工复核",
                None,
                str(requirements),
            )
        return _reason(
            "other_restrictions",
            RuleResult.PASS,
            "other_restrictions_empty",
            "岗位无结构化其他限制",
            None,
            None,
        )

    @staticmethod
    def _remarks(requirement: str) -> MatchReason:
        if requirement.strip():
            return _reason(
                "remarks",
                RuleResult.UNKNOWN,
                "remarks_manual_review",
                "岗位备注需要人工复核",
                None,
                requirement,
            )
        return _reason("remarks", RuleResult.PASS, "remarks_empty", "岗位无附加备注", None, None)


@dataclass(frozen=True, slots=True)
class PositionMatchQuery:
    """transport 无关的岗位匹配查询。"""

    exam_type: str | None = None
    year: int | None = None
    province: str | None = None
    city: str | None = None
    keyword: str | None = None
    match_filter: PositionMatchFilter = PositionMatchFilter.POTENTIAL
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True, slots=True)
class PositionMatchItem:
    """一个岗位及其资格判断。"""

    position: PositionItem
    match_status: PositionMatchStatus
    reasons: tuple[MatchReason, ...]
    missing_profile_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PositionMatchResult:
    """应用状态过滤后的正确分页结果。"""

    items: list[PositionMatchItem]
    total: int
    page: int
    page_size: int


class PositionMatchService:
    """加载权威档案、保护候选上限并执行确定性匹配。"""

    def __init__(
        self,
        users: UserRepositoryProtocol,
        positions: PositionMatchRepositoryProtocol,
        evaluator: PositionEligibilityEvaluator,
        candidate_limit: int,
    ) -> None:
        self._users = users
        self._positions = positions
        self._evaluator = evaluator
        self._candidate_limit = candidate_limit

    async def search(self, user_id: int, query: PositionMatchQuery) -> PositionMatchResult:
        """在有界候选集完成规则判断后再过滤和分页。"""
        stored_profile = await self._users.get_profile_by_user_id(user_id)
        if stored_profile is None:
            raise UserProfileNotConfirmedError
        profile = ProfileData.model_validate(stored_profile.profile)
        effective = replace(
            query,
            exam_type=query.exam_type or profile.target_exam_type,
            province=query.province or profile.target_province,
            city=query.city or profile.target_city,
        )
        candidate_query = PositionCandidateQuery(
            exam_type=effective.exam_type,
            year=effective.year,
            province=effective.province,
            city=effective.city,
            keyword=effective.keyword,
        )
        count = await self._positions.count_candidates(candidate_query)
        if count > self._candidate_limit:
            raise PositionCandidateLimitExceededError(count, self._candidate_limit)
        candidates = await self._positions.list_candidates(
            candidate_query, limit=self._candidate_limit
        )
        if len(candidates) > self._candidate_limit:
            raise PositionCandidateLimitExceededError(len(candidates), self._candidate_limit)

        matches = []
        for candidate in candidates:
            position = PositionItem.from_model(candidate)
            eligibility = self._evaluator.evaluate(profile, position)
            item = PositionMatchItem(
                position=position,
                match_status=eligibility.status,
                reasons=eligibility.reasons,
                missing_profile_fields=eligibility.missing_profile_fields,
            )
            if _matches_filter(item.match_status, query.match_filter):
                matches.append(item)

        start = (query.page - 1) * query.page_size
        return PositionMatchResult(
            items=matches[start : start + query.page_size],
            total=len(matches),
            page=query.page,
            page_size=query.page_size,
        )


def _extract_education_levels(value: str) -> set[int]:
    normalized = _normalize(value)
    matched: set[int] = set()
    for label, level in sorted(_EDUCATION_LEVELS.items(), key=lambda item: -len(item[0])):
        if label in normalized:
            matched.add(level)
            normalized = normalized.replace(label, "")
    return matched


def _split_values(value: str) -> list[str]:
    return [
        token.strip()
        for token in _SPLIT_PATTERN.split(unicodedata.normalize("NFKC", value))
        if token.strip()
    ]


def _set_rule(
    *,
    field: str,
    profile_value: str | None,
    requirement: str,
    aliases: dict[str, str],
    special_allowed: dict[str, set[str]] | None = None,
) -> MatchReason:
    if _is_unlimited(requirement):
        return _reason(
            field,
            RuleResult.PASS,
            f"{field}_unlimited",
            "岗位该项条件不限",
            profile_value,
            requirement,
        )
    if not requirement.strip():
        return _reason(
            field,
            RuleResult.UNKNOWN,
            f"{field}_requirement_missing",
            "岗位该项要求缺失",
            profile_value,
            requirement,
        )
    if profile_value is None:
        return _reason(
            field,
            RuleResult.UNKNOWN,
            f"{field}_profile_missing",
            "用户该项信息未填写",
            None,
            requirement,
        )
    normalized_profile = aliases.get(_normalize(profile_value))
    normalized_requirement = _normalize(requirement)
    allowed = (special_allowed or {}).get(normalized_requirement)
    if allowed is None:
        values = _split_values(requirement)
        normalized_values = [aliases.get(_normalize(value)) for value in values]
        if not normalized_values or any(value is None for value in normalized_values):
            return _reason(
                field,
                RuleResult.UNKNOWN,
                f"{field}_unrecognized",
                "该项信息无法可靠规范化",
                profile_value,
                requirement,
            )
        allowed = {value for value in normalized_values if value is not None}
    if normalized_profile is None:
        return _reason(
            field,
            RuleResult.UNKNOWN,
            f"{field}_profile_unrecognized",
            "用户该项信息无法可靠规范化",
            profile_value,
            requirement,
        )
    passed = normalized_profile in allowed
    return _reason(
        field,
        RuleResult.PASS if passed else RuleResult.FAIL,
        f"{field}_satisfied" if passed else f"{field}_not_satisfied",
        "用户信息满足岗位该项要求" if passed else "用户信息不满足岗位该项要求",
        profile_value,
        requirement,
    )


def _parse_location(value: str) -> tuple[str | None, str | None]:
    normalized = _normalize(value)
    for word in ("户籍所在地", "户籍", "生源地", "生源", "仅限", "限"):
        normalized = normalized.replace(word, "")
    province = next((item for item in _PROVINCES if item in normalized), None)
    city: str | None = None
    if province in _MUNICIPALITIES:
        city = province
    else:
        remainder = normalized
        if province is not None:
            index = normalized.find(province)
            remainder = normalized[index + len(province) :]
            remainder = remainder.removeprefix("壮族自治区").removeprefix("回族自治区")
            remainder = remainder.removeprefix("维吾尔自治区").removeprefix("自治区")
            remainder = remainder.removeprefix("特别行政区").removeprefix("省")
        city_match = re.match(r"([\u4e00-\u9fff]{2,8})市", remainder)
        if city_match is not None:
            city = city_match.group(1)
    return province, city


def _matches_filter(status: PositionMatchStatus, selected: PositionMatchFilter) -> bool:
    if selected is PositionMatchFilter.ALL:
        return True
    if selected is PositionMatchFilter.POTENTIAL:
        return status in {PositionMatchStatus.ELIGIBLE, PositionMatchStatus.UNCERTAIN}
    return status.value == selected.value
