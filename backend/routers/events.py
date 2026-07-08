import json
import uuid

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from database import get_db

router = APIRouter(tags=["events"])


class CompleteHabitRequest(BaseModel):
    idempotency_key: str
    client_timestamp: Optional[str] = None


class EventOut(BaseModel):
    id: str
    user_id: int
    idempotency_key: str
    event_type: str
    payload: dict
    server_timestamp: str
    version: int


def _row_to_event(row: aiosqlite.Row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "idempotency_key": row["idempotency_key"],
        "event_type": row["event_type"],
        "payload": json.loads(row["payload"]),
        "server_timestamp": row["server_timestamp"],
        "version": row["version"],
    }


@router.post("/habits/{habit_id}/complete", response_model=EventOut, status_code=201)
async def complete_habit(
    habit_id: int, body: CompleteHabitRequest, db: aiosqlite.Connection = Depends(get_db)
):
    cur = await db.execute(
        "SELECT id FROM habits WHERE id = ? AND user_id = 1 AND archived_at IS NULL",
        (habit_id,),
    )
    if not await cur.fetchone():
        raise HTTPException(status_code=404, detail="Habit not found")

    # Fast path: this idempotency key was already processed, return the
    # original event instead of writing a duplicate.
    cur = await db.execute(
        "SELECT id, user_id, idempotency_key, event_type, payload, server_timestamp, version"
        " FROM events WHERE user_id = 1 AND idempotency_key = ?",
        (body.idempotency_key,),
    )
    existing = await cur.fetchone()
    if existing:
        return _row_to_event(existing)

    event_id = str(uuid.uuid4())
    payload = json.dumps({"habit_id": habit_id, "client_timestamp": body.client_timestamp})

    # BEGIN IMMEDIATE takes the write lock up front so the MAX(version)+1
    # read and the insert are atomic against concurrent completions from
    # this same user (SQLite only ever has one writer at a time anyway).
    await db.execute("BEGIN IMMEDIATE")
    try:
        cur = await db.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM events WHERE user_id = 1")
        (version,) = await cur.fetchone()
        cur = await db.execute(
            "INSERT INTO events (id, user_id, idempotency_key, event_type, payload, version)"
            " VALUES (?, 1, ?, 'habit_completed', ?, ?)"
            " RETURNING id, user_id, idempotency_key, event_type, payload, server_timestamp, version",
            (event_id, body.idempotency_key, payload, version),
        )
        row = await cur.fetchone()
        await db.commit()
        return _row_to_event(row)
    except aiosqlite.IntegrityError:
        # Lost a race with a concurrent request using the same key.
        await db.rollback()
        cur = await db.execute(
            "SELECT id, user_id, idempotency_key, event_type, payload, server_timestamp, version"
            " FROM events WHERE user_id = 1 AND idempotency_key = ?",
            (body.idempotency_key,),
        )
        row = await cur.fetchone()
        return _row_to_event(row)
