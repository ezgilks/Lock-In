from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import aiosqlite
from database import get_db

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryCreate(BaseModel):
    name: str
    color: str = "#6366f1"


class CategoryOut(BaseModel):
    id: int
    user_id: int
    name: str
    color: str


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(body: CategoryCreate, db: aiosqlite.Connection = Depends(get_db)):
    cur = await db.execute(
        "INSERT INTO categories (user_id, name, color) VALUES (1, ?, ?) RETURNING id, user_id, name, color",
        (body.name, body.color),
    )
    row = await cur.fetchone()
    await db.commit()
    return dict(row)


@router.get("", response_model=list[CategoryOut])
async def list_categories(db: aiosqlite.Connection = Depends(get_db)):
    cur = await db.execute(
        "SELECT id, user_id, name, color FROM categories WHERE user_id = 1"
    )
    rows = await cur.fetchall()
    return [dict(r) for r in rows]
