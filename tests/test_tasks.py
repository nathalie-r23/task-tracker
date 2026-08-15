import time
from datetime import datetime, timedelta, timezone

# Long enough to outlast the system clock's tick. Windows updates the wall
# clock roughly every 8-16ms, so two calls to datetime.now() either side of a
# fast request usually return the *same* value — see
# docs/midcourse/verification.md for the measurement.
CLOCK_TICK_S = 0.05


def _days_from_today(days: int) -> str:
    """ISO date `days` away from today in UTC — matches the server's overdue clock."""
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


def _parse(timestamp: str) -> datetime:
    """Parse the API's ISO timestamps. Compared as datetimes rather than strings
    because the serialiser omits microseconds when they happen to be zero."""
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def test_create_task_valid_returns_201_with_full_body(client):
    response = client.post(
        "/tasks",
        json={
            "title": "Write tests",
            "description": "Cover all endpoints",
            "status": "ToDo",
            "priority": "High",
            "assignee": "alice",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], str) and body["id"]
    assert body["title"] == "Write tests"
    assert body["description"] == "Cover all endpoints"
    assert body["status"] == "ToDo"
    assert body["priority"] == "High"
    assert body["assignee"] == "alice"
    assert isinstance(body["created_at"], str) and body["created_at"]
    assert isinstance(body["updated_at"], str) and body["updated_at"]


def test_create_task_missing_title_returns_422(client):
    response = client.post("/tasks", json={"description": "no title"})

    assert response.status_code == 422


def test_create_task_blank_title_returns_422(client):
    response = client.post("/tasks", json={"title": "   "})

    assert response.status_code == 422


def test_create_task_invalid_priority_returns_422(client):
    response = client.post("/tasks", json={"title": "Bad priority", "priority": "Urgent"})

    assert response.status_code == 422


def test_create_task_unknown_field_returns_422(client):
    response = client.post("/tasks", json={"title": "Extra field", "unknown": "value"})

    assert response.status_code == 422


def test_list_tasks_empty_returns_200_and_empty_list(client):
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_filter_by_status_no_match_returns_200_and_empty_list(client):
    client.post("/tasks", json={"title": "Only todo", "status": "ToDo"})

    response = client.get("/tasks", params={"status": "Done"})

    assert response.status_code == 200
    assert response.json() == []


def test_list_tasks_filter_by_priority_returns_only_matches(client):
    client.post("/tasks", json={"title": "Low task", "priority": "Low"})
    client.post("/tasks", json={"title": "High task", "priority": "High"})

    response = client.get("/tasks", params={"priority": "Low"})

    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Low task"
    assert tasks[0]["priority"] == "Low"


def test_get_task_by_id_returns_task(client, created_task):
    response = client.get(f"/tasks/{created_task['id']}")

    assert response.status_code == 200
    assert response.json() == created_task


def test_get_task_by_id_not_found_returns_404_with_detail(client):
    response = client.get("/tasks/nonexistent-id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task with id nonexistent-id not found"


def test_patch_partial_update_keeps_other_fields(client, created_task):
    task_id = created_task["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"description": "updated description"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == created_task["title"]
    assert body["description"] == "updated description"
    assert body["status"] == created_task["status"]
    assert body["priority"] == created_task["priority"]
    assert body["assignee"] == created_task["assignee"]
    assert body["created_at"] == created_task["created_at"]
    # Ordering only. Whether the clock actually advanced during a sub-millisecond
    # request is the subject of test_patch_refreshes_updated_at, not this test.
    assert _parse(body["updated_at"]) >= _parse(created_task["updated_at"])


def test_patch_refreshes_updated_at(client, created_task):
    time.sleep(CLOCK_TICK_S)

    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"description": "updated description"},
    )

    assert response.status_code == 200
    body = response.json()
    assert _parse(body["updated_at"]) > _parse(created_task["updated_at"])
    assert body["created_at"] == created_task["created_at"]


def test_patch_empty_body_returns_task_unchanged(client, created_task):
    task_id = created_task["id"]

    response = client.patch(f"/tasks/{task_id}", json={})

    assert response.status_code == 200
    assert response.json() == created_task


def test_patch_unknown_field_returns_422(client, created_task):
    task_id = created_task["id"]

    response = client.patch(f"/tasks/{task_id}", json={"foo": "bar"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["type"] == "extra_forbidden"
    assert detail[0]["loc"] == ["body", "foo"]


def test_patch_blank_title_returns_422(client, created_task):
    task_id = created_task["id"]

    response = client.patch(f"/tasks/{task_id}", json={"title": "   "})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"] == ["body", "title"]
    assert "title must not be blank" in detail[0]["msg"]


def test_patch_invalid_priority_returns_422(client, created_task):
    task_id = created_task["id"]

    response = client.patch(f"/tasks/{task_id}", json={"priority": "Urgent"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"] == ["body", "priority"]
    assert detail[0]["type"] == "enum"


def test_patch_malformed_json_returns_422(client, created_task):
    task_id = created_task["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        content="{invalid",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["type"] == "json_invalid"
    assert "JSON decode error" in detail[0]["msg"]


def test_patch_not_found_returns_404(client):
    response = client.patch("/tasks/nonexistent-id", json={"title": "Nope"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Task with id nonexistent-id not found"


def test_patch_valid_transition_todo_to_inprogress_returns_200(client, created_task):
    task_id = created_task["id"]

    response = client.patch(f"/tasks/{task_id}", json={"status": "InProgress"})

    assert response.status_code == 200
    assert response.json()["status"] == "InProgress"


def test_patch_valid_transition_inprogress_to_done_returns_200(client, created_task):
    task_id = created_task["id"]
    client.patch(f"/tasks/{task_id}", json={"status": "InProgress"})

    response = client.patch(f"/tasks/{task_id}", json={"status": "Done"})

    assert response.status_code == 200
    assert response.json()["status"] == "Done"


def test_patch_invalid_transition_todo_to_done_returns_422(client, created_task):
    task_id = created_task["id"]

    response = client.patch(f"/tasks/{task_id}", json={"status": "Done"})

    assert response.status_code == 422
    assert "Invalid status transition from ToDo to Done" in response.json()["detail"]


def test_patch_same_status_returns_200(client, created_task):
    task_id = created_task["id"]

    response = client.patch(f"/tasks/{task_id}", json={"status": "ToDo"})

    assert response.status_code == 200
    assert response.json()["status"] == "ToDo"


def test_delete_existing_returns_204_no_body(client, created_task):
    response = client.delete(f"/tasks/{created_task['id']}")

    assert response.status_code == 204
    assert response.content == b""


def test_delete_missing_returns_404(client):
    response = client.delete("/tasks/nonexistent-id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task with id nonexistent-id not found"


# --- Feature 1: due dates + overdue ------------------------------------------


def test_create_task_with_due_date_returns_201_and_echoes_date(client):
    due = _days_from_today(7)

    response = client.post("/tasks", json={"title": "Ship release", "due_date": due})

    assert response.status_code == 201
    body = response.json()
    assert body["due_date"] == due
    assert body["is_overdue"] is False


def test_create_task_without_due_date_defaults_to_null_and_not_overdue(client):
    response = client.post("/tasks", json={"title": "No deadline"})

    assert response.status_code == 201
    body = response.json()
    assert body["due_date"] is None
    assert body["is_overdue"] is False


def test_create_task_malformed_due_date_returns_422(client):
    response = client.post("/tasks", json={"title": "Bad date", "due_date": "07-29-2026"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == "due_date"


def test_create_task_impossible_calendar_date_returns_422(client):
    response = client.post("/tasks", json={"title": "Bad date", "due_date": "2026-02-30"})

    assert response.status_code == 422


def test_past_due_date_marks_task_overdue(client):
    response = client.post(
        "/tasks",
        json={"title": "Late work", "due_date": _days_from_today(-1)},
    )

    assert response.status_code == 201
    assert response.json()["is_overdue"] is True


def test_due_today_is_not_overdue(client):
    """Boundary: you still have the whole day, so today is not yet late."""
    response = client.post(
        "/tasks",
        json={"title": "Due today", "due_date": _days_from_today(0)},
    )

    assert response.status_code == 201
    assert response.json()["is_overdue"] is False


def test_done_task_with_past_due_date_is_not_overdue(client):
    """Finished work is never flagged, even if it was completed late."""
    response = client.post(
        "/tasks",
        json={"title": "Finished late", "status": "Done", "due_date": _days_from_today(-5)},
    )

    assert response.status_code == 201
    assert response.json()["is_overdue"] is False


def test_patch_due_date_updates_value_and_recomputes_overdue(client, created_task):
    task_id = created_task["id"]

    response = client.patch(f"/tasks/{task_id}", json={"due_date": _days_from_today(-3)})

    assert response.status_code == 200
    body = response.json()
    assert body["due_date"] == _days_from_today(-3)
    assert body["is_overdue"] is True


def test_patch_due_date_to_null_clears_it(client):
    created = client.post(
        "/tasks",
        json={"title": "Had a deadline", "due_date": _days_from_today(-2)},
    ).json()
    assert created["is_overdue"] is True

    response = client.patch(f"/tasks/{created['id']}", json={"due_date": None})

    assert response.status_code == 200
    body = response.json()
    assert body["due_date"] is None
    assert body["is_overdue"] is False


def test_completing_an_overdue_task_clears_the_overdue_flag(client):
    created = client.post(
        "/tasks",
        json={"title": "Late but doable", "due_date": _days_from_today(-4)},
    ).json()
    assert created["is_overdue"] is True

    client.patch(f"/tasks/{created['id']}", json={"status": "InProgress"})
    response = client.patch(f"/tasks/{created['id']}", json={"status": "Done"})

    assert response.status_code == 200
    body = response.json()
    assert body["due_date"] == _days_from_today(-4)
    assert body["is_overdue"] is False


def test_patch_unrelated_field_preserves_due_date(client):
    created = client.post(
        "/tasks",
        json={"title": "Keep my date", "due_date": _days_from_today(5)},
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"priority": "High"})

    assert response.status_code == 200
    body = response.json()
    assert body["priority"] == "High"
    assert body["due_date"] == created["due_date"]


def test_list_overdue_true_returns_only_overdue_tasks(client):
    client.post("/tasks", json={"title": "Late", "due_date": _days_from_today(-1)})
    client.post("/tasks", json={"title": "Future", "due_date": _days_from_today(1)})
    client.post("/tasks", json={"title": "No date"})

    response = client.get("/tasks", params={"overdue": "true"})

    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert titles == ["Late"]


def test_list_overdue_false_returns_only_non_overdue_tasks(client):
    client.post("/tasks", json={"title": "Late", "due_date": _days_from_today(-1)})
    client.post("/tasks", json={"title": "Future", "due_date": _days_from_today(1)})
    client.post("/tasks", json={"title": "No date"})

    response = client.get("/tasks", params={"overdue": "false"})

    assert response.status_code == 200
    titles = sorted(t["title"] for t in response.json())
    assert titles == ["Future", "No date"]


def test_list_overdue_omitted_returns_all_tasks(client):
    client.post("/tasks", json={"title": "Late", "due_date": _days_from_today(-1)})
    client.post("/tasks", json={"title": "Future", "due_date": _days_from_today(1)})

    response = client.get("/tasks")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_overdue_combines_with_priority_filter(client):
    client.post(
        "/tasks",
        json={"title": "Late high", "priority": "High", "due_date": _days_from_today(-1)},
    )
    client.post(
        "/tasks",
        json={"title": "Late low", "priority": "Low", "due_date": _days_from_today(-1)},
    )

    response = client.get("/tasks", params={"overdue": "true", "priority": "High"})

    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert titles == ["Late high"]


def test_list_overdue_with_no_matches_returns_200_and_empty_list(client):
    client.post("/tasks", json={"title": "Future", "due_date": _days_from_today(3)})

    response = client.get("/tasks", params={"overdue": "true"})

    assert response.status_code == 200
    assert response.json() == []


def test_list_invalid_overdue_value_returns_422(client):
    response = client.get("/tasks", params={"overdue": "maybe"})

    assert response.status_code == 422


# --- Feature 2: tags ---------------------------------------------------------


def test_create_task_with_tags_returns_201_and_echoes_tags(client):
    response = client.post(
        "/tasks",
        json={"title": "Tagged task", "tags": ["backend", "urgent"]},
    )

    assert response.status_code == 201
    assert response.json()["tags"] == ["backend", "urgent"]


def test_create_task_without_tags_defaults_to_empty_list(client):
    response = client.post("/tasks", json={"title": "Untagged"})

    assert response.status_code == 201
    assert response.json()["tags"] == []


def test_create_task_trims_whitespace_around_tags(client):
    response = client.post("/tasks", json={"title": "Padded", "tags": ["  backend  "]})

    assert response.status_code == 201
    assert response.json()["tags"] == ["backend"]


def test_create_task_blank_tag_returns_422(client):
    response = client.post("/tasks", json={"title": "Blank tag", "tags": ["ok", "   "]})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail[0]["loc"] == ["body", "tags"]
    assert "tags must not be blank" in detail[0]["msg"]


def test_create_task_overlong_tag_returns_422(client):
    response = client.post("/tasks", json={"title": "Long tag", "tags": ["x" * 25]})

    assert response.status_code == 422
    assert "at most 24 characters" in response.json()["detail"][0]["msg"]


def test_create_task_too_many_tags_returns_422(client):
    response = client.post(
        "/tasks",
        json={"title": "Too many", "tags": [f"tag{n}" for n in range(11)]},
    )

    assert response.status_code == 422
    assert "at most 10 tags allowed" in response.json()["detail"][0]["msg"]


def test_create_task_deduplicates_tags_case_insensitively(client):
    response = client.post(
        "/tasks",
        json={"title": "Dupes", "tags": ["Bug", "bug", "BUG", "ui"]},
    )

    assert response.status_code == 201
    assert response.json()["tags"] == ["Bug", "ui"]


def test_create_task_non_string_tag_returns_422(client):
    response = client.post("/tasks", json={"title": "Bad type", "tags": [123]})

    assert response.status_code == 422


def test_patch_replaces_tags_wholesale(client):
    created = client.post(
        "/tasks",
        json={"title": "Retag me", "tags": ["old"]},
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"tags": ["new", "shiny"]})

    assert response.status_code == 200
    assert response.json()["tags"] == ["new", "shiny"]


def test_patch_tags_to_null_clears_them(client):
    created = client.post("/tasks", json={"title": "Clear me", "tags": ["temp"]}).json()

    response = client.patch(f"/tasks/{created['id']}", json={"tags": None})

    assert response.status_code == 200
    assert response.json()["tags"] == []


def test_patch_unrelated_field_preserves_tags(client):
    created = client.post(
        "/tasks",
        json={"title": "Keep my tags", "tags": ["backend", "urgent"]},
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"priority": "High"})

    assert response.status_code == 200
    body = response.json()
    assert body["priority"] == "High"
    assert body["tags"] == ["backend", "urgent"]


def test_patch_blank_tag_returns_422_and_leaves_task_untouched(client):
    created = client.post("/tasks", json={"title": "Safe", "tags": ["keep"]}).json()

    response = client.patch(f"/tasks/{created['id']}", json={"tags": [""]})

    assert response.status_code == 422
    assert client.get(f"/tasks/{created['id']}").json()["tags"] == ["keep"]


def test_patch_title_to_null_returns_422_and_leaves_task_untouched(client):
    # A required field has nothing to clear to, so null is a validation error
    # rather than a 500 from rebuilding the task with a null title.
    created = client.post("/tasks", json={"title": "Keep this title"}).json()

    response = client.patch(f"/tasks/{created['id']}", json={"title": None})

    assert response.status_code == 422
    assert client.get(f"/tasks/{created['id']}").json()["title"] == "Keep this title"


def test_patch_description_to_null_clears_it(client):
    # Mirrors create, where a null description is stored as "".
    created = client.post(
        "/tasks", json={"title": "Clear my description", "description": "temporary"}
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"description": None})

    assert response.status_code == 200
    assert response.json()["description"] == ""


def test_patch_nullable_fields_never_return_500(client):
    # Every field that accepts null on the wire answers with a real status code:
    # 200 when it clears, 422 when it cannot. None of them may 500.
    created = client.post(
        "/tasks",
        json={
            "title": "Null sweep",
            "description": "d",
            "assignee": "alice",
            "due_date": "2026-01-01",
            "tags": ["t"],
        },
    ).json()

    for field in ("title", "description", "assignee", "due_date", "tags"):
        response = client.patch(f"/tasks/{created['id']}", json={field: None})
        assert response.status_code in (200, 422), f"{field} returned {response.status_code}"


def test_list_filter_by_tag_returns_only_matching_tasks(client):
    client.post("/tasks", json={"title": "Has it", "tags": ["backend", "api"]})
    client.post("/tasks", json={"title": "Lacks it", "tags": ["frontend"]})
    client.post("/tasks", json={"title": "No tags"})

    response = client.get("/tasks", params={"tag": "backend"})

    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert titles == ["Has it"]


def test_list_filter_by_tag_is_case_insensitive(client):
    client.post("/tasks", json={"title": "Bug task", "tags": ["Bug"]})

    response = client.get("/tasks", params={"tag": "BUG"})

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_filter_by_unknown_tag_returns_200_and_empty_list(client):
    client.post("/tasks", json={"title": "Tagged", "tags": ["backend"]})

    response = client.get("/tasks", params={"tag": "nonexistent"})

    assert response.status_code == 200
    assert response.json() == []


def test_list_filter_combines_tag_and_overdue(client):
    client.post(
        "/tasks",
        json={"title": "Late backend", "tags": ["backend"], "due_date": _days_from_today(-1)},
    )
    client.post(
        "/tasks",
        json={"title": "Late frontend", "tags": ["frontend"], "due_date": _days_from_today(-1)},
    )
    client.post("/tasks", json={"title": "On time backend", "tags": ["backend"]})

    response = client.get("/tasks", params={"tag": "backend", "overdue": "true"})

    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert titles == ["Late backend"]


# --- Search (?q=) ---------------------------------------------------------


def test_search_matches_title_case_insensitively(client):
    client.post("/tasks", json={"title": "Ship Release Notes"})
    client.post("/tasks", json={"title": "Unrelated"})

    response = client.get("/tasks", params={"q": "release"})

    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == ["Ship Release Notes"]


def test_search_matches_a_fragment_inside_a_word(client):
    client.post("/tasks", json={"title": "Ship release notes"})

    response = client.get("/tasks", params={"q": "eleas"})

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_search_matches_description(client):
    client.post("/tasks", json={"title": "Opaque title", "description": "migrate the database"})
    client.post("/tasks", json={"title": "Other", "description": "nothing relevant"})

    response = client.get("/tasks", params={"q": "DATABASE"})

    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == ["Opaque title"]


def test_search_does_not_match_assignee(client):
    client.post("/tasks", json={"title": "Some task", "assignee": "alice"})

    response = client.get("/tasks", params={"q": "alice"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_does_not_match_tags(client):
    client.post("/tasks", json={"title": "Some task", "tags": ["backend"]})

    response = client.get("/tasks", params={"q": "backend"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_with_no_matches_returns_200_and_empty_list(client):
    client.post("/tasks", json={"title": "Ship release notes"})

    response = client.get("/tasks", params={"q": "zzzznope"})

    assert response.status_code == 200
    assert response.json() == []


def test_search_with_empty_query_returns_every_task(client):
    client.post("/tasks", json={"title": "One"})
    client.post("/tasks", json={"title": "Two"})

    response = client.get("/tasks", params={"q": ""})

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_with_whitespace_only_query_returns_every_task(client):
    client.post("/tasks", json={"title": "One"})
    client.post("/tasks", json={"title": "Two"})

    response = client.get("/tasks", params={"q": "   "})

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_trims_surrounding_whitespace_from_the_query(client):
    client.post("/tasks", json={"title": "Ship release notes"})

    response = client.get("/tasks", params={"q": "  release  "})

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_search_treats_the_query_as_literal_text_not_a_pattern(client):
    client.post("/tasks", json={"title": "Ship release notes"})
    client.post("/tasks", json={"title": "Regex chars .* live here"})

    response = client.get("/tasks", params={"q": ".*"})

    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == ["Regex chars .* live here"]


def test_search_combines_with_tag_and_overdue(client):
    client.post(
        "/tasks",
        json={
            "title": "Fix api timeout",
            "tags": ["backend"],
            "due_date": _days_from_today(-1),
        },
    )
    client.post(
        "/tasks",
        json={"title": "Fix api layout", "tags": ["frontend"], "due_date": _days_from_today(-1)},
    )
    client.post("/tasks", json={"title": "Fix api docs", "tags": ["backend"]})

    response = client.get("/tasks", params={"q": "api", "tag": "backend", "overdue": "true"})

    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == ["Fix api timeout"]


def test_search_combines_with_priority(client):
    client.post("/tasks", json={"title": "Urgent api work", "priority": "High"})
    client.post("/tasks", json={"title": "Calm api work", "priority": "Low"})

    response = client.get("/tasks", params={"q": "api", "priority": "High"})

    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == ["Urgent api work"]


def test_search_handles_tasks_with_no_description(client):
    client.post("/tasks", json={"title": "Bare task"})

    response = client.get("/tasks", params={"q": "bare"})

    assert response.status_code == 200
    assert len(response.json()) == 1
