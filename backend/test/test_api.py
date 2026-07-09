import sqlite3

from conftest import TEST_DB


def _query(sql, params=()):
    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _category_state(category_id):
    rows = _query("SELECT * FROM category_state WHERE category_id = ?", (category_id,))
    return rows[0]


def _user_state(user_id=1):
    rows = _query("SELECT * FROM user_state WHERE user_id = ?", (user_id,))
    return rows[0]


def _create_category(client, name="Fitness"):
    return client.post("/categories", json={"name": name}).json()


def _create_habit(client, category_id, base_xp=50, name="Pushups"):
    return client.post("/habits", json={"category_id": category_id, "name": name, "base_xp": base_xp}).json()


def _complete(client, habit_id, idempotency_key):
    return client.post(f"/habits/{habit_id}/complete", json={"idempotency_key": idempotency_key})


def test_complete_habit_updates_projections(client):
    category = _create_category(client)
    habit = _create_habit(client, category["id"], base_xp=50)

    _complete(client, habit["id"], "k1")
    _complete(client, habit["id"], "k2")  # same day -> repeat decay

    state = _category_state(category["id"])
    assert state["current_xp"] == 56  # 50*1.02 round=51, then 50*1.02*0.1 round=5
    assert state["streak_days"] == 1

    assert _user_state()["ovr"] == 1.0


def test_duplicate_idempotency_key_does_not_reapply(client):
    category = _create_category(client)
    habit = _create_habit(client, category["id"], base_xp=50)

    _complete(client, habit["id"], "k1")
    before = _category_state(category["id"])

    resp = _complete(client, habit["id"], "k1")  # duplicate
    assert resp.status_code == 201

    assert _category_state(category["id"]) == before


def test_rebuild_matches_live_state(client):
    category = _create_category(client)
    habit = _create_habit(client, category["id"], base_xp=50)

    for i in range(4):
        _complete(client, habit["id"], f"k{i}")

    before_cat = _category_state(category["id"])
    before_user = _user_state()

    resp = client.post("/admin/users/1/rebuild")
    assert resp.status_code == 204

    assert _category_state(category["id"]) == before_cat
    assert _user_state() == before_user


def test_rebuild_nonexistent_user_404s(client):
    resp = client.post("/admin/users/999/rebuild")
    assert resp.status_code == 404


def test_complete_nonexistent_habit_404s(client):
    resp = client.post("/habits/999/complete", json={"idempotency_key": "k"})
    assert resp.status_code == 404


def test_dashboard_shows_untouched_category_at_level_1(client):
    fitness = _create_category(client, name="Fitness")
    _create_category(client, name="Reading")  # never completed
    habit = _create_habit(client, fitness["id"], base_xp=50)
    _complete(client, habit["id"], "k1")

    dashboard = client.get("/dashboard").json()
    by_name = {c["name"]: c for c in dashboard["categories"]}

    assert by_name["Fitness"]["current_xp"] == 51
    assert by_name["Fitness"]["current_level"] == 1
    assert by_name["Reading"]["current_xp"] == 0
    assert by_name["Reading"]["current_level"] == 1
    assert by_name["Reading"]["xp_for_next_level"] == by_name["Fitness"]["xp_for_next_level"]

    # Both categories are level 1 -> harmonic mean is 1.0 even though only
    # one has ever been completed (the OVR-neglect fix this test guards).
    assert dashboard["ovr"] == 1.0


def test_dashboard_empty_before_any_completions(client):
    _create_category(client, name="Fitness")
    dashboard = client.get("/dashboard").json()
    assert dashboard["ovr"] == 0.0
    category = dashboard["categories"][0]
    assert category["current_xp"] == 0
    assert category["current_level"] == 1
    assert category["xp_for_current_level"] == 0  # level 1 has no real floor
