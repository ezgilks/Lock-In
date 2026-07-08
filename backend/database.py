import aiosqlite
import os

DB_PATH = os.environ.get("DB_PATH", "lock_in.db")

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
    finally:
        await db.close()

async def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        sql = f.read()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.executescript(sql)
        await db.commit()
        # Seed a default dev user if none exists
        await db.execute(
            "INSERT OR IGNORE INTO users (id, username) VALUES (1, 'dev')"
        )
        await db.commit()
