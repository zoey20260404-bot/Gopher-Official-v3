"""岗位匹配 Application Service 单元测试。"""

import pytest

from gopher_agent.domain.matching import PositionMatchFilter, PositionMatchStatus
from gopher_agent.domain.profile import ProfileData
from gopher_agent.models.position import Position
from gopher_agent.models.user import User, UserProfile
from gopher_agent.repositories.types import PositionCandidateQuery
from gopher_agent.services.exceptions import (
    PositionCandidateLimitExceededError,
    UserProfileNotConfirmedError,
)
from gopher_agent.services.matching import (
    PositionEligibilityEvaluator,
    PositionMatchQuery,
    PositionMatchService,
)


def build_position(position_id: int, **overrides: object) -> Position:
    values: dict[str, object] = {
        "exam_type": "国考",
        "year": 2026,
        "province": "广东",
        "city": "广州",
        "department": "税务局",
        "position_name": f"岗位{position_id}",
        "position_code": f"P{position_id}",
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
    }
    values.update(overrides)
    position = Position(**values)
    position.id = position_id
    return position


class FakeUserRepository:
    def __init__(self, profile: UserProfile | None) -> None:
        self.profile = profile

    async def add(self, user: User) -> User:
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        return None

    async def get_by_username(self, username: str) -> User | None:
        return None

    async def get_profile_by_user_id(self, user_id: int) -> UserProfile | None:
        return self.profile


class FakeMatchRepository:
    def __init__(self, positions: list[Position], *, count: int | None = None) -> None:
        self.positions = positions
        self.count = len(positions) if count is None else count
        self.count_query: PositionCandidateQuery | None = None
        self.list_query: PositionCandidateQuery | None = None
        self.limit: int | None = None

    async def count_candidates(self, query: PositionCandidateQuery) -> int:
        self.count_query = query
        return self.count

    async def list_candidates(self, query: PositionCandidateQuery, *, limit: int) -> list[Position]:
        self.list_query = query
        self.limit = limit
        return self.positions


def build_service(
    profile: ProfileData | None,
    repository: FakeMatchRepository,
    *,
    candidate_limit: int = 2000,
) -> PositionMatchService:
    stored = None
    if profile is not None:
        stored = UserProfile(user_id=7, profile=profile.model_dump(mode="json"))
    return PositionMatchService(
        FakeUserRepository(stored),
        repository,
        PositionEligibilityEvaluator(),
        candidate_limit,
    )


async def test_service_uses_profile_targets_then_filters_and_paginates_matches() -> None:
    profile = ProfileData(
        age=24,
        target_exam_type="国考",
        target_province="广东",
        target_city="广州",
    )
    repository = FakeMatchRepository(
        [
            build_position(3),
            build_position(2, remarks="需要人工复核"),
            build_position(1, age_limit=20),
        ]
    )
    service = build_service(profile, repository)

    result = await service.search(7, PositionMatchQuery(page=2, page_size=1))

    expected_query = PositionCandidateQuery(exam_type="国考", province="广东", city="广州")
    assert repository.count_query == expected_query
    assert repository.list_query == expected_query
    assert repository.limit == 2000
    assert result.total == 2
    assert result.page == 2
    assert result.items[0].position.id == 2
    assert result.items[0].match_status is PositionMatchStatus.UNCERTAIN


async def test_explicit_filters_override_profile_and_ineligible_filter_is_exact() -> None:
    profile = ProfileData(age=24, target_province="广东")
    repository = FakeMatchRepository([build_position(1, age_limit=20), build_position(2)])
    service = build_service(profile, repository)

    result = await service.search(
        7,
        PositionMatchQuery(
            province="浙江",
            match_filter=PositionMatchFilter.INELIGIBLE,
        ),
    )

    assert repository.count_query == PositionCandidateQuery(province="浙江")
    assert result.total == 1
    assert result.items[0].position.id == 1


async def test_service_requires_confirmed_profile() -> None:
    service = build_service(None, FakeMatchRepository([]))

    with pytest.raises(UserProfileNotConfirmedError):
        await service.search(7, PositionMatchQuery())


@pytest.mark.parametrize(
    ("count", "positions"),
    [(3, []), (2, [build_position(1), build_position(2), build_position(3)])],
)
async def test_service_rejects_count_or_read_race_above_candidate_limit(
    count: int, positions: list[Position]
) -> None:
    service = build_service(
        ProfileData(),
        FakeMatchRepository(positions, count=count),
        candidate_limit=2,
    )

    with pytest.raises(PositionCandidateLimitExceededError) as captured:
        await service.search(7, PositionMatchQuery())

    assert captured.value.limit == 2
