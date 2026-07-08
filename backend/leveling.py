"""Pure leveling/XP functions — no DB access, fully unit-testable in isolation."""


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
