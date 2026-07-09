"""Pure leveling/XP functions — no DB access, fully unit-testable in isolation."""

from datetime import date


def xp_for_level(level: int) -> int:
    return int(100 * (level**1.5))


def level_for_xp(xp: int) -> int:
    level = 1
    while xp_for_level(level + 1) <= xp:
        level += 1
    return level


def xp_award(base_xp: int, streak_days: int, daily_completions_today: int) -> int:
    streak_mult = min(1 + streak_days * 0.02, 2.0)
    repeat_decay = 1.0 if daily_completions_today == 0 else 0.1
    return round(base_xp * streak_mult * repeat_decay)


def ovr(category_xps: dict[str, int]) -> float:
    # Harmonic mean penalizes neglected categories more than arithmetic mean
    levels = [level_for_xp(xp) for xp in category_xps.values()]
    n = len(levels)
    return n / sum(1 / l for l in levels) if n else 0.0


def next_category_state(
    prev_xp: int,
    prev_streak_days: int,
    prev_last_completed_date: str | None,
    base_xp: int,
    event_date: str,
    prior_completions_same_day: int,
) -> tuple[int, int, int]:
    """Fold one habit-completion event into category projection state.

    Pure and order-dependent only on (prev state, this event) — this is what
    makes replay-from-log reproduce the same result as live processing, as
    long as events are folded in `version` order. Dates are 'YYYY-MM-DD'
    strings (SQLite's `date()` / `datetime('now')` format).

    Returns (new_xp, new_level, new_streak_days).
    """
    if prev_last_completed_date == event_date:
        new_streak = prev_streak_days
    elif prev_last_completed_date is not None and (
        date.fromisoformat(event_date) - date.fromisoformat(prev_last_completed_date)
    ).days == 1:
        new_streak = prev_streak_days + 1
    else:
        new_streak = 1

    delta = xp_award(base_xp, streak_days=new_streak, daily_completions_today=prior_completions_same_day)
    new_xp = prev_xp + delta
    return new_xp, level_for_xp(new_xp), new_streak
