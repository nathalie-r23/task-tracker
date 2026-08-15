# Task Tracker — Architecture (targeted read)

*Written from three files only: `app/main.py`, `app/models.py`,
`app/storage.py`. Anything outside them is marked not visible.*

## 1. What the app does

A task tracker exposing a REST API over tasks, their comments, and an activity
log. Tasks carry a status, priority, assignee, due date and tags; comments are
appended to tasks; every field change is recorded as an activity entry. The API
title is "Task Tracker API" and its description states: in-memory storage, no
auth, no database. Storage is three module-level Python containers, so all data
is lost when the process stops. Whether a user interface exists is not visible
from the files I read.

## 2. Data model

**Task** — `id` (UUID string), `title` (required, trimmed, ≤200 chars),
`description` (defaults to `""`), `status` (`ToDo` · `InProgress` · `Done`,
default `ToDo`), `priority` (`Low` · `Medium` · `High`, default `Medium`),
`assignee`, `due_date`, `tags` (≤10, each ≤24 chars, trimmed, duplicates
dropped case-insensitively keeping the first spelling), `created_at` /
`updated_at` (UTC). Two read-only derived fields: `is_overdue`, a computed
property — due date strictly before today in UTC **and** status not `Done` — and
`comment_count`, stamped by the storage layer on every read.

**Comment** — `id`, `task_id`, `author` (optional, ≤80 chars, blank stored as
null), `body` (required, trimmed, ≤2000 chars), `created_at`. No update or
delete route exists in `main.py`.

**ActivityEntry** — `id`, `task_id`, `task_title` (a snapshot from the time of
the event), `kind` (`created` · `updated` · `commented` · `deleted`), `field`,
`from_value`, `to_value`, `at`. Values are flattened to strings; only plain
strings are truncated at 80 characters — enums, dates and lists render
untruncated.

## 3. Request flow — creating a task

1. `POST /tasks` reaches `create_task` in `app/main.py`.
2. The body is parsed into `TaskCreate`. Validators trim and check `title` and
   `tags`; `extra="forbid"` means unknown keys are rejected. Validators raise
   `ValueError`.
3. The handler calls `storage.add_task()`. It does **not** call
   `validate_status_transition` — the docstring states the allow-list runs only
   on `PATCH`, so a task may be created directly as `Done`.
4. Storage assigns a UUID and one UTC timestamp used for both `created_at` and
   `updated_at`, normalises a null description to `""`, stores the task, and
   records a `created` activity entry.
5. The task is returned through `_with_comment_count()`. Declared response
   status: **201**.

## 4. Key files

| File | Role |
|---|---|
| `app/main.py` | App factory, CORS middleware, and every task/comment/activity route (read) |
| `app/models.py` | Pydantic models, field validation, the overdue rule, activity-value flattening (read) |
| `app/storage.py` | In-memory stores, filtering, activity recording, activity limits (read) |
| `app/business_rules.py` | Imported for `validate_status_transition`; contents not visible from the files I read |
| `app/core/config.py` | Imported for `settings`; contents not visible from the files I read |
| `app/api/routes/health.py` | Registered as the only router; its routes are not visible from the files I read |

Any other file in the repository is not visible from the files I read.

## 5. Conventions

**Validation** lives in the models, not the routes. Model validators raise
`ValueError`. What HTTP status that produces is not visible from the files I
read — it is the framework's behaviour, not stated in these three files. Routes
raise `HTTPException` with an explicit 404 for unknown ids.

**Storage** is three module-level containers: tasks and comments as dicts, the
activity log as a flat list deliberately not keyed by task, because entries
outlive the tasks they describe. Derived values are computed on read.
`update_task` uses `exclude_unset` to distinguish "not sent" from "sent as
null". Deleting a task removes its comments but keeps its activity.

**Error handling** is entirely explicit — there is no `except` clause in any of
the three files. Unknown ids produce 404. On `PATCH`, the 404 is raised before
the transition rule is evaluated.

**Frontend/backend interaction** — CORS allows the origin `"null"` plus a regex
matching any `localhost` or `127.0.0.1` port, with credentials disabled. Code
comments in `main.py` say this covers opening a frontend file directly from disk
and serving it on an arbitrary local port. No static files are mounted. The
frontend itself is not visible from the files I read.

## 6. Not visible or assumptions

- The specific allowed status transitions. `main.py` shows a 422 is raised when
  a transition is not in `VALID_TRANSITIONS`, but which pairs are allowed is not
  visible from the files I read.
- What `/health` returns, and what `settings` contains.
- `settings` is imported in `main.py` and never referenced anywhere else in that
  file. Whether it is used elsewhere is not visible from the files I read.
- Whether any tests exist, and any build, container or CI configuration.
- Python and library versions.

---

*Strategy C — targeted context: three anchor files, with a standing rule to
write "not visible from the files I read" rather than infer from framework
convention. The gap this exposed is structural: `business_rules.py` was not in
the anchor set, so the status-transition allow-list — the app's most
distinctive rule — could not be stated at all.*
