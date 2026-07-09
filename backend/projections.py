"""Projection updates for category_state/user_state.

Both the live completion path and the rebuild-from-log admin endpoint call
`apply_completion` for each habit_completed event, in `version` order. That's
what guarantees a rebuild reproduces exactly the state live processing would
have produced — there's only one code path that mutates projections.
"""

import json

import aiosqlite

from leveling import next_category_state, ovr


async def apply_completion(
    db: aiosqlite.Connection,
    user_id: int,
    category_id: int,
    base_xp: int,
    event_date: str,
    event_version: int,
) -> None:
    await db.execute(
        "INSERT OR IGNORE INTO category_state (category_id) VALUES (?)", (category_id,)
    )

    cur = await db.execute(
        "SELECT current_xp, streak_days, last_completed_date FROM category_state"
        " WHERE category_id = ?",
        (category_id,),
    )
    prev_xp, prev_streak, prev_last_date = await cur.fetchone()

    cur = await db.execute(
        "SELECT COUNT(*) FROM events"
        " WHERE user_id = ? AND event_type = 'habit_completed'"
        "   AND json_extract(payload, '$.category_id') = ?"
        "   AND date(server_timestamp) = ?"
        "   AND version < ?",
        (user_id, category_id, event_date, event_version),
    )
    (prior_completions_same_day,) = await cur.fetchone()

    new_xp, new_level, new_streak = next_category_state(
        prev_xp, prev_streak, prev_last_date, base_xp, event_date, prior_completions_same_day
    )

    await db.execute(
        "UPDATE category_state SET current_xp = ?, current_level = ?, streak_days = ?,"
        " last_completed_date = ?, updated_through_version = ? WHERE category_id = ?",
        (new_xp, new_level, new_streak, event_date, event_version, category_id),
    )

    # LEFT JOIN so a category with zero completions ever (no category_state
    # row yet) still counts toward OVR as xp=0/level=1 — otherwise a
    # never-touched category would be invisible to the harmonic mean instead
    # of dragging it down, defeating the neglect-penalizing point of ovr().
    cur = await db.execute(
        "SELECT c.id, COALESCE(cs.current_xp, 0) FROM categories c"
        " LEFT JOIN category_state cs ON cs.category_id = c.id WHERE c.user_id = ?",
        (user_id,),
    )
    rows = await cur.fetchall()
    category_xps = {str(row[0]): row[1] for row in rows}
    new_ovr = ovr(category_xps)

    await db.execute(
        "INSERT INTO user_state (user_id, ovr, updated_through_version) VALUES (?, ?, ?)"
        " ON CONFLICT(user_id) DO UPDATE SET ovr = excluded.ovr,"
        " updated_through_version = excluded.updated_through_version",
        (user_id, new_ovr, event_version),
    )


async def rebuild_user(db: aiosqlite.Connection, user_id: int) -> None:
    """Delete this user's projections and replay their event log from scratch."""
    await db.execute(
        "DELETE FROM category_state WHERE category_id IN"
        " (SELECT id FROM categories WHERE user_id = ?)",
        (user_id,),
    )
    await db.execute("DELETE FROM user_state WHERE user_id = ?", (user_id,))

    cur = await db.execute(
        "SELECT id FROM categories WHERE user_id = ?", (user_id,)
    )
    for (category_id,) in await cur.fetchall():
        await db.execute(
            "INSERT OR IGNORE INTO category_state (category_id) VALUES (?)", (category_id,)
        )

    cur = await db.execute(
        "SELECT payload, server_timestamp, version FROM events"
        " WHERE user_id = ? AND event_type = 'habit_completed' ORDER BY version ASC",
        (user_id,),
    )
    for payload_json, server_timestamp, version in await cur.fetchall():
        payload = json.loads(payload_json)
        await apply_completion(
            db,
            user_id=user_id,
            category_id=payload["category_id"],
            base_xp=payload["base_xp"],
            event_date=server_timestamp[:10],
            event_version=version,
        )
