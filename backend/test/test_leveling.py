from datetime import date, timedelta

from hypothesis import given, strategies as st

from leveling import level_for_xp, next_category_state, ovr, xp_award, xp_for_level

DATE_STRATEGY = st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 1, 1)).map(str)


@given(st.integers(min_value=1, max_value=1000))
def test_level_for_xp_inverts_xp_for_level(level):
    assert level_for_xp(xp_for_level(level)) == level


@given(st.integers(min_value=0, max_value=10_000_000))
def test_level_for_xp_monotonic(xp):
    assert level_for_xp(xp) <= level_for_xp(xp + 1)


@given(
    base_xp=st.integers(min_value=0, max_value=10_000),
    streak_days=st.integers(min_value=0, max_value=1000),
    daily_completions_today=st.integers(min_value=0, max_value=1000),
)
def test_xp_award_bounded(base_xp, streak_days, daily_completions_today):
    # streak_mult caps at 2.0, repeat_decay caps at 1.0 (first completion of the day)
    award = xp_award(base_xp, streak_days, daily_completions_today)
    assert 0 <= award <= base_xp * 2


@given(
    prev_xp=st.integers(min_value=0, max_value=100_000),
    prev_streak=st.integers(min_value=0, max_value=1000),
    base_xp=st.integers(min_value=0, max_value=10_000),
    event_date=DATE_STRATEGY,
    prior_completions=st.integers(min_value=0, max_value=100),
)
def test_next_category_state_xp_never_decreases(prev_xp, prev_streak, base_xp, event_date, prior_completions):
    new_xp, new_level, _ = next_category_state(prev_xp, prev_streak, None, base_xp, event_date, prior_completions)
    assert new_xp >= prev_xp
    assert new_level >= level_for_xp(prev_xp)


@given(
    prev_xp=st.integers(min_value=0, max_value=100_000),
    prev_streak=st.integers(min_value=1, max_value=1000),
    base_xp=st.integers(min_value=1, max_value=10_000),
    prior_completions=st.integers(min_value=0, max_value=100),
    days_ago=st.integers(min_value=2, max_value=3650),
)
def test_streak_resets_after_a_gap(prev_xp, prev_streak, base_xp, prior_completions, days_ago):
    event_date = date(2025, 6, 15)
    prev_last = event_date - timedelta(days=days_ago)
    _, _, new_streak = next_category_state(
        prev_xp, prev_streak, str(prev_last), base_xp, str(event_date), prior_completions
    )
    assert new_streak == 1


@given(
    prev_xp=st.integers(min_value=0, max_value=100_000),
    prev_streak=st.integers(min_value=1, max_value=1000),
    base_xp=st.integers(min_value=1, max_value=10_000),
    prior_completions=st.integers(min_value=0, max_value=100),
)
def test_streak_increments_on_consecutive_day(prev_xp, prev_streak, base_xp, prior_completions):
    event_date = date(2025, 6, 15)
    prev_last = event_date - timedelta(days=1)
    _, _, new_streak = next_category_state(
        prev_xp, prev_streak, str(prev_last), base_xp, str(event_date), prior_completions
    )
    assert new_streak == prev_streak + 1


@given(
    prev_xp=st.integers(min_value=0, max_value=100_000),
    prev_streak=st.integers(min_value=1, max_value=1000),
    base_xp=st.integers(min_value=1, max_value=10_000),
    prior_completions=st.integers(min_value=0, max_value=100),
)
def test_streak_unchanged_on_same_day_repeat(prev_xp, prev_streak, base_xp, prior_completions):
    event_date = date(2025, 6, 15)
    _, _, new_streak = next_category_state(
        prev_xp, prev_streak, str(event_date), base_xp, str(event_date), prior_completions
    )
    assert new_streak == prev_streak


@given(
    prev_xp=st.integers(min_value=0, max_value=100_000),
    prev_streak=st.integers(min_value=0, max_value=1000),
    base_xp=st.integers(min_value=0, max_value=10_000),
    event_date=DATE_STRATEGY,
    prior_completions=st.integers(min_value=0, max_value=100),
)
def test_next_category_state_deterministic(prev_xp, prev_streak, base_xp, event_date, prior_completions):
    # Guards against hidden non-determinism (e.g. reading the real wall-clock
    # date instead of the passed event_date) creeping into a "pure" function —
    # replay-equals-live-processing depends on this holding.
    a = next_category_state(prev_xp, prev_streak, None, base_xp, event_date, prior_completions)
    b = next_category_state(prev_xp, prev_streak, None, base_xp, event_date, prior_completions)
    assert a == b


@given(
    xps=st.dictionaries(
        st.text(min_size=1, max_size=5),
        st.integers(min_value=0, max_value=100_000),
        min_size=1,
        max_size=10,
    )
)
def test_ovr_bounded_by_min_and_max_level(xps):
    levels = [level_for_xp(xp) for xp in xps.values()]
    result = ovr(xps)
    # Harmonic mean of a single value can round a hair above it in floating
    # point (e.g. 1/(1/49) -> 49.00000000000001), hence the epsilon.
    assert min(levels) - 1e-9 <= result <= max(levels) + 1e-9


def test_ovr_empty_is_zero():
    assert ovr({}) == 0.0
