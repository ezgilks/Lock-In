# Lock In — Session Handoff

_Last updated: 2026-07-09 (session 4)_

## What this project is

Event-sourced habit/XP tracker MVP. Full spec is the project brief (habits →
events → XP → OVR). Every user action is an immutable event; level/OVR/streaks
are projections rebuilt from the event log, never hand-edited.

Repo: https://github.com/ezgilks/Lock-In.git (pushed to `main`)

## Build order (do not skip ahead)

1. **DONE** — Event log table + `POST /habits/{id}/complete`, idempotency-key
   deduped, no projection writes yet.
2. **DONE** — Projection layer: `category_state`/`user_state` updated in the
   same transaction as the event write. `POST /admin/users/{id}/rebuild`
   replays a user's events from scratch. See "Current state of the code"
   below for how it's structured.
3. **DONE** — Hypothesis property tests for `leveling.py` (pure, isolated),
   plus a handful of integration tests hitting `/complete` and
   `/admin/users/{id}/rebuild` through a real (throwaway) SQLite DB. See
   "Current state of the code" and "Step 3 verification" below.
4. **DONE** — React + Tailwind dashboard (radar chart per category, OVR
   number, level progress bars), reading only from a new `GET /dashboard`
   endpoint. Verified rendering against real backend data with a headless
   browser screenshot. See "Current state of the code" and "Step 4
   verification" below.
5. **DONE** — Complete-habit button in the dashboard UI (frontend-only;
   backend already supported it). See "Current state of the code" and
   "Step 5 verification" below.
6. **NEXT** — Not scoped yet. Candidates: category/habit management UI
   (currently backend-only via curl), auth/multi-user support. See "Next
   step for the next session" at the bottom.

## Current state of the code

- `backend/schema.sql` — full schema includes `category_state` and
  `user_state` tables, now populated by the projection layer.
- `backend/leveling.py` — pure `xp_for_level`, `level_for_xp`, `xp_award`,
  `ovr` functions, plus `next_category_state(prev_xp, prev_streak_days,
  prev_last_completed_date, base_xp, event_date, prior_completions_same_day)`
  — folds one habit-completion event into (new_xp, new_level, new_streak).
  This is the one place streak-continuation (`last_completed_date` is
  yesterday → +1; is today → unchanged; older/None → reset to 1) and
  same-day repeat-decay are decided. No tests yet — this is the prime
  target for the step-3 Hypothesis tests.
- `backend/projections.py` — new. `apply_completion()` does the DB side for
  one event: upserts `category_state` (reading prior state + a same-day
  prior-completions count, calling `next_category_state`, then writing xp/
  level/streak/last_completed_date/updated_through_version), then recomputes
  and upserts `user_state.ovr` from all of the user's current category XPs.
  `rebuild_user()` deletes a user's projections and calls `apply_completion`
  once per `habit_completed` event in `version` order — it's the *same*
  function as the live path, which is what guarantees replay reproduces
  live state exactly.
- `backend/routers/events.py` — `POST /habits/{habit_id}/complete`. Now also
  snapshots `category_id`/`base_xp` into the event payload at completion
  time (not just `habit_id`), so replay isn't affected if a habit's
  `base_xp` or category is edited later — it uses what was true when the
  event happened, not the habit's current row. Calls `apply_completion`
  inside the same `BEGIN IMMEDIATE` transaction as the event insert, before
  commit. Duplicate `idempotency_key` still short-circuits before any of
  this and just returns the original event (verified this doesn't
  re-apply projections). Version numbers are assigned atomically per-user
  inside `BEGIN IMMEDIATE`.
- `backend/routers/admin.py` — new. `POST /admin/users/{id}/rebuild` → 204,
  404 if the user doesn't exist. Wraps `rebuild_user` in its own
  `BEGIN IMMEDIATE`.
- `backend/routers/categories.py`, `habits.py` — CRUD, no projection logic.
- `backend/routers/dashboard.py` — new. `GET /dashboard` → `{ovr, categories:
  [{id, name, color, current_xp, current_level, streak_days,
  xp_for_current_level, xp_for_next_level}]}`. `LEFT JOIN`s `categories` to
  `category_state` so a category with zero completions ever still shows up
  (at level 1 / 0 xp) instead of being silently absent.
  `xp_for_current_level` is 0 for level 1 (there's no real xp floor for
  level 1 — `xp_for_level(1)` is the threshold for reaching level 2, not a
  floor) and `xp_for_level(current_level)` otherwise; exposed so the
  frontend doesn't need to reimplement `leveling.py`'s formula to draw a
  progress bar.
- **Bug fix in `projections.py`**: `apply_completion`'s OVR recompute used
  to `JOIN category_state` (inner join), so a category with zero
  completions ever was invisible to the harmonic mean instead of dragging
  it down — defeating the whole point of `ovr()` penalizing neglected
  categories. Changed to `LEFT JOIN` with `COALESCE(current_xp, 0)`. Caught
  while building the dashboard's OVR display, not before.
- `frontend/` — Vite + React 19 + Tailwind v4 (`@tailwindcss/vite` plugin,
  no separate config file needed) + Recharts. Dev server proxies `/api/*`
  to `localhost:8000` (stripping the `/api` prefix) — see `vite.config.js`.
  `src/api.js` — `getDashboard()` (`/api/dashboard`), `getHabits()`
  (`/api/habits`), `completeHabit(habitId)` (POSTs `/api/habits/{id}
  /complete` with a fresh `crypto.randomUUID()` idempotency key per call —
  each button click is a new logical completion, not a retry, so it gets
  its own key; the *button* is disabled while a request is in flight to
  stop accidental double-clicks from creating two completions).
  `src/components/`: `OverallRating` (big OVR number), `CategoryRadarChart`
  (one Recharts `RadarChart`, one axis per category, value = `current_level`
  — note a 2-category account renders as a near-straight line, not a
  polygon; that's an inherent property of 2-axis radar charts, not a bug),
  `CategoryProgressList` (color-coded bar per category using
  `xp_for_current_level`/`xp_for_next_level` for progress *within* the
  current level, a 🔥 streak indicator when `streak_days > 0`, and now a
  "Complete" button per habit — habits are grouped by `category_id` and
  passed in as a `Map` built in `App.jsx` from `GET /habits`, since
  `/dashboard` only returns category-level projections, not habits).
  `src/App.jsx` fetches `/dashboard` + `/habits` together on mount and
  after every completion; has a manual Refresh button too (no
  polling/websockets — out of scope). Completed habits stay in the list
  with an always-active Complete button (habits are repeatable, not
  single-use-per-day) — there's no "already done today" visual state yet,
  see next steps.
- `backend/pytest.ini` — new. Just `pythonpath = .` so tests can
  `import main`/`leveling`/`projections` the same way the app does
  (absolute imports, no package prefix). Run tests with `cd backend &&
  pytest` (venv activated).
- `backend/test/conftest.py` — new. Sets `DB_PATH` to a throwaway
  `test/_test_lockin.db` *before* `main`/`database` are imported (module-
  level, so it takes effect on first import). The `client` fixture deletes
  any leftover db file, opens a `fastapi.testclient.TestClient` (which runs
  the real `lifespan` — schema creation + dev-user seed — on `__enter__`),
  yields it, then deletes the db file again. Every test gets a fully fresh
  DB; nothing here ever touches the real `backend/lock_in.db`.
- `backend/test/test_leveling.py` — new. Hypothesis property tests, all
  pure (no DB): `level_for_xp`/`xp_for_level` inverse + monotonic, `xp_award`
  bounded in `[0, base_xp*2]`, `next_category_state` never decreases xp,
  streak reset/increment/unchanged rules for gap>1/exactly-1/same-day, and
  a determinism check (same inputs → same outputs, guarding against
  accidentally reading the real wall-clock date instead of `event_date`).
- `backend/test/test_api.py` — uses the `client` fixture plus direct
  `sqlite3` reads of `test/_test_lockin.db` for `category_state`/
  `user_state` (still no read endpoint for those raw tables, only the
  aggregated `/dashboard` view — reading the DB directly in tests avoids
  adding API surface that's only needed for tests). Covers: completing a
  habit twice same-day produces the expected decayed XP total, duplicate
  `idempotency_key` doesn't reapply projections, `/admin/users/1/rebuild`
  reproduces identical state after several completions, 404s for a
  nonexistent habit/user, and (added in step 4) `/dashboard` shows an
  untouched category at level 1 and folds it into OVR correctly.

## Environment gotcha

System Python is 3.13, but `pydantic-core` (via pydantic 2.7.4) fails to
build from source on 3.13 — PyO3 doesn't support it yet. The venv was created
with Homebrew's `python@3.12` instead:

```bash
cd backend
/opt/homebrew/bin/python3.12 -m venv .venv   # if recreating
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

`backend/.venv/`, `backend/lock_in.db*`, and `__pycache__/` are gitignored.

## Step 2 verification (done this session)

Ran manually against a throwaway `DB_PATH` (not the dev `lock_in.db`, which
already has real data in it from earlier sessions — left untouched):

- Created a category + habit (`base_xp=50`), completed it twice same day.
  Completion 1: streak 1 (first-ever), no same-day repeat → 50 × 1.02 × 1.0
  = 51 XP. Completion 2: same day → decay kicks in → 50 × 1.02 × 0.1 = 5 XP.
  `category_state.current_xp` = 56, `streak_days` = 1, `current_level` = 1
  (below the level-2 threshold of ~283 XP). `user_state.ovr` = 1.0.
- Repeated completion 1's `idempotency_key` — returned the original event,
  confirmed `current_xp` did not change (no double-apply).
- Called `/admin/users/1/rebuild` — `category_state`/`user_state` came back
  byte-identical to the live-processed values above.
- Confirmed 404s: completing a nonexistent habit, rebuilding a nonexistent
  user.

Not yet tested at that point: streak continuation across multiple real
days, and concurrent-completion races on `/complete`. Streak
continuation/reset is now covered by the step-3 Hypothesis tests below
(`test_streak_resets_after_a_gap`, `test_streak_increments_on_consecutive_day`,
`test_streak_unchanged_on_same_day_repeat`) operating directly on
`next_category_state` with fabricated dates — concurrent-completion races
are still untested.

## Step 3 verification

`cd backend && source .venv/bin/activate && pytest -q` → **15 passed** at
the time, run twice with `--hypothesis-seed=random` to check for flakiness
(none seen at the time — see step 4's note on a floating-point edge case
Hypothesis found later). Nothing here touches the real `backend/lock_in.db`
— tests use their own throwaway file, deleted before and after each test.

- 8 Hypothesis property tests in `test_leveling.py`, pure/no DB.
- 5 integration tests in `test_api.py` against a real (throwaway) SQLite DB
  through the full FastAPI app + lifespan.
- 2 plain unit tests (`ovr` edge cases).

## Step 4 verification (done this session)

- `pytest -q` → **17 passed** (added the two `/dashboard` tests above).
  Hypothesis's broader search on a reworded run also turned up a genuine
  bug in `test_ovr_bounded_by_min_and_max_level` itself (not in `ovr()`):
  the harmonic mean of a single value can round a hair above it in
  floating point (`1/(1/49)` → `49.00000000000001`), failing a strict
  `<=` bound. Fixed with a `1e-9` epsilon on the assertion — this was a
  test bug, not a product bug.
- Backend manually smoke-tested against a throwaway `DB_PATH`: created 3
  categories (Fitness, Reading, Coding), habits in the first two, 5
  same-day completions on one habit (confirms decay math on real data:
  60×1.02=61, then four more at 60×1.02×0.1≈6 each = 85 total) and 1 on
  the other. `GET /dashboard` returned the expected shape and numbers,
  including Coding (zero completions) correctly appearing at level 1/0xp.
- Frontend verified visually: ran `npm run dev`, drove headless Chromium
  via Playwright (no `chromium-cli` available in this environment — used
  raw Playwright directly instead, same idea) against the dev server
  proxying to the backend above, waited for the dashboard to render,
  screenshotted it, and checked `console --errors` equivalent (page
  console listener) — zero errors. Screenshot confirmed: OVR "1.0", radar
  chart with 3 axes (one per category), color-coded progress bars with
  correct XP numbers and 🔥 streak indicators on the two touched
  categories. Not yet exercised: what the radar chart looks like once
  categories are at genuinely different levels (everything in this test
  was still level 1 — 282 xp needed to reach level 2, and this took only
  ~90 xp of seed data).

## Step 5 verification (done this session)

No backend changes this session (`pytest -q` still **17 passed**, unchanged
from step 4 — confirms this really was frontend-only work). Frontend
verified visually against a fresh throwaway `DB_PATH`: seeded 2 categories
(Fitness with habits Gym + Stretch, Reading with Read 20 pages), screenshot
before any completions (OVR 0.0, all buttons enabled, 0/282 xp everywhere),
then drove 45 clicks on Gym's Complete button via headless Chromium
(Playwright) and screenshotted again. Confirmed: Fitness crossed into
**level 2** (325/519 xp, progress bar correctly rescaled to the new level's
range), streak showed 🔥1, OVR recalculated to **1.3** (harmonic mean of
levels 2 and 1 — `2/(1/2+1/1) = 1.333`, matches), Reading unaffected, zero
console errors throughout. This is the first time the dashboard has shown
anything above level 1 — step 4's verification never crossed that
threshold.

## Next step for the next session

Ended this session live-testing the frontend against the real dev
`lock_in.db` (has a "Fitness" category with a "Gym" habit from earlier
sessions) — it works, but user flagged the frontend still needs polish
before moving to the next big feature. No specifics captured yet on what
exactly felt rough; ask at the start of next session rather than assuming
it's one of the items below.

Reasonable next candidates, none prioritized yet:

- **Category/habit management UI** — currently backend-only via curl;
  `POST /categories` and `POST /habits` exist but have no frontend.
  `DELETE /habits/{id}` (archive) also exists and is unused by the UI.
- **"Already completed today" indicator** — habits currently always show
  an active Complete button, even right after being completed. Not
  incorrect (habits are repeatable, decay just makes repeats worth less)
  but might be worth a visual cue so it's not surprising that clicking
  again gives much less XP.
- **Auth / multi-user** — everything is still hardcoded to `user_id = 1`.
  Explicitly out of scope until the core loop feels solid, per this
  project's `CLAUDE.md`.
- Still-untested edge cases from earlier steps: concurrent-completion
  races on `/complete`, and streak continuation across genuinely different
  calendar days end-to-end through the API (covered at the pure
  `next_category_state` level, not through `/complete` itself, since that
  endpoint always stamps "now").
