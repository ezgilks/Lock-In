# CLAUDE.md — Lock In

Guidance for Claude Code when working in this repo. This file describes the
project's vision and durable conventions — it should change rarely, and only
when the architecture or invariants actually change. For "what's done, what's
next," see `HANDOFF.md` instead.

## Vision

Lock In is an event-sourced habit/XP tracker. Users complete habits; habits
belong to categories; completions earn XP; XP determines a level per
category and an overall rating (OVR) across categories. The point of the
event-sourcing design is that **nothing is ever hand-edited** — every user
action is appended to an immutable event log, and all derived state
(levels, XP, streaks, OVR) is a projection that can always be thrown away
and rebuilt from that log. If projection state and a from-scratch replay
ever disagree, that's a bug in the projection logic, not the log.

## Architecture

```
event log (events table, append-only)
      │
      ▼
projections (category_state, user_state — derived, rebuildable)
      │
      ▼
API layer (routers/) — reads projections, never computes XP/levels inline
```

- `backend/schema.sql` — table definitions. `events` is append-only.
  `category_state` / `user_state` are projections.
- `backend/leveling.py` — pure functions (`xp_for_level`, `level_for_xp`,
  `xp_award`, `ovr`). No DB access, fully unit-testable in isolation. Any
  change to leveling math belongs here, not inline in a router.
- `backend/database.py` — `get_db()` is an async-generator FastAPI
  dependency (connects once per request, yields, closes in `finally`).
  Don't wrap it in `async with db:` in routers — that double-awaits an
  already-started aiosqlite connection and was a bug we hit once already.
- `backend/projections.py` — `apply_completion()` (DB-side projection
  update for one event) and `rebuild_user()` (replays a user's event log
  through the same function, in `version` order). Only one code path ever
  mutates `category_state`/`user_state` — that's what guarantees rebuild
  reproduces live-processed state exactly. Don't add a second write path.
- `backend/routers/` — `categories.py`, `habits.py` (plain CRUD),
  `events.py` (`POST /habits/{id}/complete` — the only place events get
  written), `admin.py` (`POST /admin/users/{id}/rebuild`), `dashboard.py`
  (`GET /dashboard` — the only read path for projection data; computes
  derived display fields like `xp_for_next_level` server-side so the
  frontend never reimplements `leveling.py`'s formulas).
- `frontend/` — Vite + React + Tailwind v4 + Recharts. Reads projection
  data only from `GET /dashboard`, never recomputes levels/XP client-side.
  The only write it performs is `POST /habits/{id}/complete` (the
  Complete button) — same idempotent endpoint as any other client, nothing
  frontend-specific. Dev server
  proxies `/api/*` to the backend on `:8000` (see `vite.config.js`).

## Testing

- Backend: `cd backend && pytest -q` (needs the venv active). Tests never
  touch the real `backend/lock_in.db` — `test/conftest.py` points `DB_PATH`
  at a throwaway file, wiped before/after each test.
- Pure logic (`leveling.py`) gets Hypothesis property tests, not just
  example-based unit tests — these functions are the one place replay
  correctness and XP/streak math actually live, so they're worth the extra
  scrutiny. Reach for a property (bounds, monotonicity, determinism, a
  before/after invariant) before reaching for a handful of example asserts.
- API-level behavior (idempotency, rebuild-matches-live, 404s) gets
  integration tests through the real FastAPI app (`fastapi.testclient
  .TestClient`, which runs the actual `lifespan`), not mocked routers.

## Invariants (don't violate these without discussion)

- **Events are immutable.** Never `UPDATE` or `DELETE` a row in `events`.
  Corrections are new events, not edits.
- **Projections are derived, never hand-edited.** Any write to
  `category_state`/`user_state` must be reproducible by replaying events
  from scratch via the rebuild endpoint.
- **Idempotency keys dedupe writes.** `POST /habits/{id}/complete` must
  return the original event on a repeated `idempotency_key`, not create a
  duplicate or error.
- **Version numbers are atomic and monotonic per user.** Assigned inside a
  `BEGIN IMMEDIATE` transaction alongside the event insert.
- **XP increments are atomic.** Use `UPDATE ... SET current_xp = current_xp
  + :delta`, never read-modify-write from application code.
- **No optimistic locking yet.** A `version` column on projections is the
  planned future upgrade path if concurrent writers become a problem —
  don't build it preemptively.

## Environment

System Python is 3.13, but `pydantic-core` (pydantic 2.7.4) won't build on
3.13 yet. Use Homebrew's `python@3.12` for the venv:

```bash
cd backend
/opt/homebrew/bin/python3.12 -m venv .venv   # if recreating
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload          # :8000
```

```bash
cd frontend
npm run dev                        # :5173, proxies /api/* to :8000
```

`backend/.venv/`, `backend/lock_in.db*`, `__pycache__/`, and
`frontend/node_modules/` are gitignored.

There's currently no auth — everything is hardcoded to a single seeded
`user_id = 1` dev user. Don't build multi-user support unless asked; it's
out of scope until the MVP's core loop (events → projections → dashboard)
works end to end.

## Working on this project

- **Update `HANDOFF.md` as you complete tasks.** It's the to-do list and
  session log — mark items done, add newly-discovered next steps, note any
  gotchas hit along the way. This file (`CLAUDE.md`) should not need to
  change just because a task got done.
- Follow the build order in `HANDOFF.md`; don't skip ahead to the frontend
  or to tests before the projection layer is solid.
- Prefer verifying behavior end-to-end (curl the endpoint, check the DB
  directly) over trusting that code "looks right," especially for anything
  touching the event log or projections.
