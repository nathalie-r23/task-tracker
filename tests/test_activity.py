from datetime import datetime, timedelta, timezone

from app import storage


def _days_from_today(days: int) -> str:
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


def _task(client, **overrides):
    payload = {"title": "Tracked"}
    payload.update(overrides)
    return client.post("/tasks", json=payload).json()


def _activity(client, task_id):
    response = client.get(f"/tasks/{task_id}/activity")
    assert response.status_code == 200
    return response.json()


def test_creating_a_task_records_a_created_entry(client):
    task = _task(client, title="Ship it")

    entries = _activity(client, task["id"])

    assert len(entries) == 1
    assert entries[0]["kind"] == "created"
    assert entries[0]["task_id"] == task["id"]
    assert entries[0]["task_title"] == "Ship it"
    assert entries[0]["field"] is None


def test_activity_for_unknown_task_returns_404(client):
    response = client.get("/tasks/does-not-exist/activity")

    assert response.status_code == 404


def test_patch_records_one_entry_per_changed_field(client):
    task = _task(client)

    client.patch(
        f"/tasks/{task['id']}",
        json={"priority": "High", "assignee": "alice"},
    )

    updates = [e for e in _activity(client, task["id"]) if e["kind"] == "updated"]
    assert sorted(e["field"] for e in updates) == ["assignee", "priority"]


def test_patch_records_the_before_and_after_values(client):
    task = _task(client, priority="Medium")

    client.patch(f"/tasks/{task['id']}", json={"priority": "High"})

    entry = _activity(client, task["id"])[0]
    assert entry["kind"] == "updated"
    assert entry["field"] == "priority"
    assert entry["from_value"] == "Medium"
    assert entry["to_value"] == "High"


def test_patch_that_resends_the_current_value_records_nothing(client):
    task = _task(client, priority="Medium")

    client.patch(f"/tasks/{task['id']}", json={"priority": "Medium"})

    assert [e["kind"] for e in _activity(client, task["id"])] == ["created"]


def test_empty_patch_records_nothing(client):
    task = _task(client)

    client.patch(f"/tasks/{task['id']}", json={})

    assert [e["kind"] for e in _activity(client, task["id"])] == ["created"]


def test_rejected_patch_records_nothing(client):
    task = _task(client)

    assert client.patch(f"/tasks/{task['id']}", json={"status": "Done"}).status_code == 422

    assert [e["kind"] for e in _activity(client, task["id"])] == ["created"]


def test_activity_is_returned_newest_first(client):
    task = _task(client)
    client.patch(f"/tasks/{task['id']}", json={"priority": "High"})
    client.patch(f"/tasks/{task['id']}", json={"priority": "Low"})

    entries = _activity(client, task["id"])

    assert [e["kind"] for e in entries] == ["updated", "updated", "created"]
    assert entries[0]["to_value"] == "Low"
    assert entries[1]["to_value"] == "High"


def test_status_change_records_the_enum_value_not_its_name(client):
    task = _task(client)

    client.patch(f"/tasks/{task['id']}", json={"status": "InProgress"})

    entry = _activity(client, task["id"])[0]
    assert entry["from_value"] == "ToDo"
    assert entry["to_value"] == "InProgress"


def test_due_date_change_records_iso_dates(client):
    tomorrow = _days_from_today(1)
    task = _task(client, due_date=_days_from_today(-1))

    client.patch(f"/tasks/{task['id']}", json={"due_date": tomorrow})

    entry = _activity(client, task["id"])[0]
    assert entry["field"] == "due_date"
    assert entry["from_value"] == _days_from_today(-1)
    assert entry["to_value"] == tomorrow


def test_tag_change_records_a_comma_joined_list(client):
    task = _task(client, tags=["backend"])

    client.patch(f"/tasks/{task['id']}", json={"tags": ["backend", "urgent"]})

    entry = _activity(client, task["id"])[0]
    assert entry["from_value"] == "backend"
    assert entry["to_value"] == "backend, urgent"


def test_clearing_tags_records_an_empty_to_value(client):
    task = _task(client, tags=["backend"])

    client.patch(f"/tasks/{task['id']}", json={"tags": None})

    entry = _activity(client, task["id"])[0]
    assert entry["field"] == "tags"
    assert entry["from_value"] == "backend"
    assert entry["to_value"] is None


def test_long_values_are_truncated_in_the_log(client):
    task = _task(client)

    client.patch(f"/tasks/{task['id']}", json={"description": "x" * 500})

    entry = _activity(client, task["id"])[0]
    assert len(entry["to_value"]) == 80
    assert entry["to_value"].endswith("…")


def test_commenting_records_a_commented_entry(client):
    task = _task(client)

    client.post(f"/tasks/{task['id']}/comments", json={"author": "alice", "body": "Nice work"})

    entry = _activity(client, task["id"])[0]
    assert entry["kind"] == "commented"
    assert entry["from_value"] == "alice"
    assert entry["to_value"] == "Nice work"
    assert entry["field"] is None


# --- Board-wide feed (GET /activity) --------------------------------------


def test_feed_returns_entries_from_every_task_newest_first(client):
    first = _task(client, title="First")
    second = _task(client, title="Second")
    client.patch(f"/tasks/{first['id']}", json={"priority": "High"})

    feed = client.get("/activity").json()

    assert [(e["kind"], e["task_title"]) for e in feed] == [
        ("updated", "First"),
        ("created", "Second"),
        ("created", "First"),
    ]


def test_feed_is_empty_before_anything_happens(client):
    response = client.get("/activity")

    assert response.status_code == 200
    assert response.json() == []


def test_feed_can_be_filtered_by_kind(client):
    task = _task(client)
    client.patch(f"/tasks/{task['id']}", json={"priority": "High"})
    client.post(f"/tasks/{task['id']}/comments", json={"body": "hi"})

    feed = client.get("/activity", params={"kind": "updated"}).json()

    assert [e["kind"] for e in feed] == ["updated"]


def test_feed_rejects_an_unknown_kind(client):
    response = client.get("/activity", params={"kind": "exploded"})

    assert response.status_code == 422


def test_feed_can_be_filtered_by_task(client):
    first = _task(client, title="First")
    _task(client, title="Second")

    feed = client.get("/activity", params={"task_id": first["id"]}).json()

    assert [e["task_title"] for e in feed] == ["First"]


def test_feed_for_an_unknown_task_returns_empty_not_404(client):
    response = client.get("/activity", params={"task_id": "does-not-exist"})

    assert response.status_code == 200
    assert response.json() == []


def test_feed_honours_the_limit(client):
    task = _task(client)
    for priority in ["High", "Low", "Medium", "High"]:
        client.patch(f"/tasks/{task['id']}", json={"priority": priority})

    feed = client.get("/activity", params={"limit": 2}).json()

    assert len(feed) == 2
    # Newest kept, not the first two written.
    assert feed[0]["to_value"] == "High"


def test_feed_defaults_to_fifty_entries(client):
    task = _task(client)
    for index in range(60):
        client.patch(f"/tasks/{task['id']}", json={"title": f"rename {index}"})

    assert len(client.get("/activity").json()) == 50


def test_feed_rejects_a_limit_outside_the_allowed_range(client):
    assert client.get("/activity", params={"limit": 0}).status_code == 422
    assert client.get("/activity", params={"limit": 201}).status_code == 422


def test_feed_records_the_title_as_it_was_at_the_time(client):
    task = _task(client, title="Old name")
    client.patch(f"/tasks/{task['id']}", json={"title": "New name"})

    feed = client.get("/activity").json()

    # The rename entry is filed under the new name; the creation keeps the old.
    assert feed[0]["task_title"] == "New name"
    assert feed[-1]["task_title"] == "Old name"


def test_status_change_appears_on_the_feed_with_from_and_to(client):
    task = _task(client)

    client.patch(f"/tasks/{task['id']}", json={"status": "InProgress"})

    entry = client.get("/activity", params={"kind": "updated"}).json()[0]
    assert entry["field"] == "status"
    assert entry["from_value"] == "ToDo"
    assert entry["to_value"] == "InProgress"


def test_activity_is_scoped_to_its_own_task(client):
    first = _task(client, title="First")
    second = _task(client, title="Second")

    client.patch(f"/tasks/{first['id']}", json={"priority": "High"})

    assert [e["kind"] for e in _activity(client, second["id"])] == ["created"]


def test_deleting_a_task_records_a_deleted_entry(client):
    task = _task(client, title="Doomed")

    assert client.delete(f"/tasks/{task['id']}").status_code == 204

    feed = client.get("/activity", params={"task_id": task["id"]}).json()
    assert feed[0]["kind"] == "deleted"
    assert feed[0]["task_title"] == "Doomed"
    assert feed[0]["task_id"] == task["id"]


def test_deleted_task_activity_survives_on_the_feed(client):
    task = _task(client)
    client.patch(f"/tasks/{task['id']}", json={"priority": "High"})
    client.delete(f"/tasks/{task['id']}")

    # The task resource is gone, so its sub-resource 404s...
    assert client.get(f"/tasks/{task['id']}/activity").status_code == 404
    # ...but the history is still readable on the log.
    kinds = [e["kind"] for e in client.get("/activity", params={"task_id": task["id"]}).json()]
    assert kinds == ["deleted", "updated", "created"]
    assert any(e.task_id == task["id"] for e in storage._activity)
