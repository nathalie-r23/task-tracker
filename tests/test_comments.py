import time

from app import storage

# See tests/test_tasks.py — the wall clock ticks too slowly for a fast request
# to be observable, so anything asserting a timestamp did *not* move has to
# wait out a tick first or it passes for the wrong reason.
CLOCK_TICK_S = 0.05


def _task(client, **overrides):
    payload = {"title": "Commentable"}
    payload.update(overrides)
    return client.post("/tasks", json=payload).json()


def test_create_comment_returns_201_with_full_body(client):
    task = _task(client)

    response = client.post(
        f"/tasks/{task['id']}/comments",
        json={"author": "alice", "body": "Looks good to me"},
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], str) and body["id"]
    assert body["task_id"] == task["id"]
    assert body["author"] == "alice"
    assert body["body"] == "Looks good to me"
    assert isinstance(body["created_at"], str) and body["created_at"]


def test_create_comment_without_author_stores_null(client):
    task = _task(client)

    response = client.post(f"/tasks/{task['id']}/comments", json={"body": "Anonymous note"})

    assert response.status_code == 201
    assert response.json()["author"] is None


def test_create_comment_with_blank_author_stores_null(client):
    task = _task(client)

    response = client.post(
        f"/tasks/{task['id']}/comments", json={"author": "   ", "body": "Still fine"}
    )

    assert response.status_code == 201
    assert response.json()["author"] is None


def test_create_comment_trims_surrounding_whitespace(client):
    task = _task(client)

    response = client.post(
        f"/tasks/{task['id']}/comments", json={"author": "  bob  ", "body": "  spaced out  "}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["body"] == "spaced out"
    assert body["author"] == "bob"


def test_create_comment_with_blank_body_returns_422(client):
    task = _task(client)

    response = client.post(f"/tasks/{task['id']}/comments", json={"body": ""})

    assert response.status_code == 422


def test_create_comment_with_whitespace_only_body_returns_422(client):
    task = _task(client)

    response = client.post(f"/tasks/{task['id']}/comments", json={"body": "   "})

    assert response.status_code == 422


def test_create_comment_without_body_returns_422(client):
    task = _task(client)

    response = client.post(f"/tasks/{task['id']}/comments", json={"author": "alice"})

    assert response.status_code == 422


def test_create_comment_over_2000_characters_returns_422(client):
    task = _task(client)

    response = client.post(f"/tasks/{task['id']}/comments", json={"body": "x" * 2001})

    assert response.status_code == 422


def test_create_comment_of_exactly_2000_characters_is_accepted(client):
    task = _task(client)

    response = client.post(f"/tasks/{task['id']}/comments", json={"body": "x" * 2000})

    assert response.status_code == 201


def test_create_comment_with_over_long_author_returns_422(client):
    task = _task(client)

    response = client.post(
        f"/tasks/{task['id']}/comments", json={"author": "a" * 81, "body": "hello"}
    )

    assert response.status_code == 422


def test_create_comment_with_unknown_field_returns_422(client):
    task = _task(client)

    response = client.post(
        f"/tasks/{task['id']}/comments", json={"body": "hello", "upvotes": 3}
    )

    assert response.status_code == 422


def test_create_comment_on_unknown_task_returns_404(client):
    response = client.post("/tasks/does-not-exist/comments", json={"body": "hello"})

    assert response.status_code == 404


def test_list_comments_returns_them_oldest_first(client):
    task = _task(client)
    for text in ["first", "second", "third"]:
        client.post(f"/tasks/{task['id']}/comments", json={"body": text})

    response = client.get(f"/tasks/{task['id']}/comments")

    assert response.status_code == 200
    assert [c["body"] for c in response.json()] == ["first", "second", "third"]


def test_list_comments_on_a_new_task_returns_empty_list(client):
    task = _task(client)

    response = client.get(f"/tasks/{task['id']}/comments")

    assert response.status_code == 200
    assert response.json() == []


def test_list_comments_on_unknown_task_returns_404(client):
    response = client.get("/tasks/does-not-exist/comments")

    assert response.status_code == 404


def test_rejected_comment_leaves_the_existing_thread_untouched(client):
    task = _task(client)
    client.post(f"/tasks/{task['id']}/comments", json={"body": "keep me"})

    client.post(f"/tasks/{task['id']}/comments", json={"body": "   "})

    remaining = client.get(f"/tasks/{task['id']}/comments").json()
    assert [c["body"] for c in remaining] == ["keep me"]


def test_comments_are_scoped_to_their_own_task(client):
    first = _task(client, title="First")
    second = _task(client, title="Second")
    client.post(f"/tasks/{first['id']}/comments", json={"body": "belongs to first"})

    assert client.get(f"/tasks/{second['id']}/comments").json() == []
    assert len(client.get(f"/tasks/{first['id']}/comments").json()) == 1


def test_new_task_reports_zero_comments(client):
    task = _task(client)

    assert task["comment_count"] == 0


def test_comment_count_reflects_the_number_of_comments(client):
    task = _task(client)
    client.post(f"/tasks/{task['id']}/comments", json={"body": "one"})
    client.post(f"/tasks/{task['id']}/comments", json={"body": "two"})

    response = client.get(f"/tasks/{task['id']}")

    assert response.status_code == 200
    assert response.json()["comment_count"] == 2


def test_comment_count_is_present_on_the_list_endpoint(client):
    task = _task(client)
    client.post(f"/tasks/{task['id']}/comments", json={"body": "one"})

    listed = client.get("/tasks").json()

    assert [t["comment_count"] for t in listed] == [1]


def test_comment_count_survives_an_unrelated_patch(client):
    task = _task(client)
    client.post(f"/tasks/{task['id']}/comments", json={"body": "one"})

    response = client.patch(f"/tasks/{task['id']}", json={"priority": "High"})

    assert response.status_code == 200
    assert response.json()["comment_count"] == 1


def test_commenting_does_not_change_the_task_updated_at(client):
    task = _task(client)
    # Without this the clock would not have moved anyway, so the assertion
    # below would hold even if commenting *did* stamp the task.
    time.sleep(CLOCK_TICK_S)

    client.post(f"/tasks/{task['id']}/comments", json={"body": "just talking"})

    assert client.get(f"/tasks/{task['id']}").json()["updated_at"] == task["updated_at"]


def test_deleting_a_task_removes_its_comments(client):
    task = _task(client)
    client.post(f"/tasks/{task['id']}/comments", json={"body": "goes away"})

    assert client.delete(f"/tasks/{task['id']}").status_code == 204

    assert client.get(f"/tasks/{task['id']}/comments").status_code == 404
    assert task["id"] not in storage._comments
