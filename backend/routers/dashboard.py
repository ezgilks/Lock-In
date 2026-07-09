import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database import get_db
from leveling import xp_for_level

router = APIRouter(tags=["dashboard"])


class CategoryProgress(BaseModel):
    id: int
    name: str
    color: str
    current_xp: int
    current_level: int
    streak_days: int
    xp_for_current_level: int
    xp_for_next_level: int


class DashboardOut(BaseModel):
    ovr: float
    categories: list[CategoryProgress]


@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(db: aiosqlite.Connection = Depends(get_db)):
    # LEFT JOIN: a category with no completions yet has no category_state
    # row, and should still show up at level 1 / 0 xp rather than vanish.
    cur = await db.execute(
        "SELECT c.id, c.name, c.color,"
        "       COALESCE(cs.current_xp, 0) AS current_xp,"
        "       COALESCE(cs.current_level, 1) AS current_level,"
        "       COALESCE(cs.streak_days, 0) AS streak_days"
        " FROM categories c LEFT JOIN category_state cs ON cs.category_id = c.id"
        " WHERE c.user_id = 1",
    )
    rows = await cur.fetchall()
    categories = [
        CategoryProgress(
            id=row["id"],
            name=row["name"],
            color=row["color"],
            current_xp=row["current_xp"],
            current_level=row["current_level"],
            streak_days=row["streak_days"],
            # Level 1 has no real floor (everyone starts there at 0 xp);
            # xp_for_level(1) is a threshold for reaching level 2, not level 1.
            xp_for_current_level=0 if row["current_level"] == 1 else xp_for_level(row["current_level"]),
            xp_for_next_level=xp_for_level(row["current_level"] + 1),
        )
        for row in rows
    ]

    cur = await db.execute("SELECT ovr FROM user_state WHERE user_id = 1")
    ovr_row = await cur.fetchone()
    ovr_value = ovr_row["ovr"] if ovr_row else 0.0

    return DashboardOut(ovr=ovr_value, categories=categories)
