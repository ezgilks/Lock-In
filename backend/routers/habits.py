from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import aiosqlite
from database import get_db

router = APIRouter(prefix="/habits", tags=["habits"])


class HabitCreate(BaseModel):
    category_id: int
    name: str
    cadence: str = "daily"
    base_xp: int = 50


class HabitOut(BaseModel):
    id: int
    user_id: int
    category_id: int
    name: str
    cadence: str
    base_xp: int
    archived_at: Optional[str]


@router.post("", response_model=HabitOut, status_code=201)
async def create_habit(body: HabitCreate, db: aiosqlite.Connection = Depends(get_db)):
    # Verify category belongs to dev user
    cur = await db.execute(
        "SELECT id FROM categories WHERE id = ? AND user_id = 1",
        (body.category_id,),
    )
    if not await cur.fetchone():
        raise HTTPException(status_code=404, detail="Category not found")

    cur = await db.execute(
        "INSERT INTO habits (user_id, category_id, name, cadence, base_xp)"
        " VALUES (1, ?, ?, ?, ?) RETURNING id, user_id, category_id, name, cadence, base_xp, archived_at",
        (body.category_id, body.name, body.cadence, body.base_xp),
    )
    row = await cur.fetchone()
    await db.commit()
    return dict(row)


@router.get("", response_model=list[HabitOut])
async def list_habits(db: aiosqlite.Connection = Depends(get_db)):
    cur = await db.execute(
        "SELECT id, user_id, category_id, name, cadence, base_xp, archived_at"
        " FROM habits WHERE user_id = 1 AND archived_at IS NULL"
    )
    rows = await cur.fetchall()
    return [dict(r) for r in rows]


@router.delete("/{habit_id}", status_code=204)
async def archive_habit(habit_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cur = await db.execute(
        "UPDATE habits SET archived_at = datetime('now') WHERE id = ? AND user_id = 1",
        (habit_id,),
    )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Habit not found")
    await db.commit()
