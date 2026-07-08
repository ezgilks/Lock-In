CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#6366f1'
);

CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    category_id INTEGER NOT NULL REFERENCES categories(id),
    name TEXT NOT NULL,
    cadence TEXT NOT NULL DEFAULT 'daily',
    base_xp INTEGER NOT NULL DEFAULT 50,
    archived_at TEXT
);

-- Immutable event log — never update or delete rows here
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,                  -- uuid
    user_id INTEGER NOT NULL REFERENCES users(id),
    idempotency_key TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,                -- JSON
    server_timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    version INTEGER NOT NULL,             -- monotonic per-user sequence
    UNIQUE (user_id, idempotency_key)
);

-- Derived projections — rebuilt from events, never hand-edited directly
CREATE TABLE IF NOT EXISTS category_state (
    category_id INTEGER PRIMARY KEY REFERENCES categories(id),
    current_xp INTEGER NOT NULL DEFAULT 0,
    current_level INTEGER NOT NULL DEFAULT 1,
    streak_days INTEGER NOT NULL DEFAULT 0,
    last_completed_date TEXT,
    updated_through_version INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_state (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    ovr REAL NOT NULL DEFAULT 1.0,
    updated_through_version INTEGER NOT NULL DEFAULT 0
);
