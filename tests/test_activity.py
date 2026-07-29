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
    assert entries[0]["to_value"] == "Ship it"
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


def test_activity_is_scoped_to_its_own_task(client):
    first = _task(client, title="First")
    second = _task(client, title="Second")

    client.patch(f"/tasks/{first['id']}", json={"priority": "High"})

    assert [e["kind"] for e in _activity(client, second["id"])] == ["created"]


def test_deleting_a_task_removes_its_activity(client):
    task = _task(client)
    client.patch(f"/tasks/{task['id']}", json={"priority": "High"})

    assert client.delete(f"/tasks/{task['id']}").status_code == 204

    assert client.get(f"/tasks/{task['id']}/activity").status_code == 404
    assert task["id"] not in storage._activity
