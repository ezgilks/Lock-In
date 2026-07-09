import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from database import get_db
from projections import rebuild_user

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users/{user_id}/rebuild", status_code=204)
async def rebuild(user_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cur = await db.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not await cur.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    await db.execute("BEGIN IMMEDIATE")
    await rebuild_user(db, user_id)
    await db.commit()
