# Task Tracker — Architecture

## 1. What the app does

A Kanban task tracker: a FastAPI REST API plus a dependency-free single-file
frontend. Tasks move between three columns, carry priority, assignee, due date
and tags, and accumulate append-only comments and a per-field activity log.
Storage is in-process Python dictionaries, wiped on restart. No database, no
authentication, nothing deployed.

## 2. Data model

**Task** — `id` (UUID), `title` (required, ≤200 chars), `description`,
`status` (`ToDo` · `InProgress` · `Done`), `priority` (`Low` · `Medium` ·
`High`), `assignee`, `due_date`, `tags` (≤10, each ≤24 chars, deduplicated
case-insensitively), `created_at`/`updated_at` (UTC). Two read-only derived
fields: `is_overdue` (computed per read) and `comment_count` (stamped by the
storage layer).

**Comment** — `id`, `task_id`, `author` (optional, ≤80), `body` (required,
≤2000), `created_at`. Append-only: no edit, no delete.

**ActivityEntry** — `id`, `task_id`, `task_title` (a snapshot, not a live
lookup), `kind` (`created` · `updated` · `commented` · `deleted`), `field`,
`from_value`, `to_value`, `at`. One entry per changed field.

## 3. Request flow — creating a task

1. `POST /tasks` reaches the route in `app/main.py`.
2. FastAPI parses the body into `TaskCreate`. Field validators trim and check
   `title` and `tags`; `extra="forbid"` rejects unknown keys. Any failure
   returns 422 before handler code runs.
3. The handler calls `storage.add_task()`. The status-transition allow-list is
   **not** applied here — it runs only on `PATCH` — so a task may be created
   directly as `Done`.
4. Storage assigns a UUID and one UTC timestamp used for both `created_at` and
   `updated_at`, stores the task, and records a `created` activity entry.
5. The task is returned stamped with `comment_count`, and `is_overdue` is
   computed during serialisation. Response: **201**.

## 4. Key files

| File | Role |
|---|---|
| `app/main.py` | App factory, CORS, and every task/comment/activity route |
| `app/models.py` | Pydantic models, field validation, overdue rule, activity-value flattening |
| `app/storage.py` | In-memory stores, filtering, activity recording, comment-count stamping |
| `app/business_rules.py` | `VALID_TRANSITIONS` allow-list and its 422 guard |
| `app/core/config.py` | `PORT` / `APP_ENV` via pydantic-settings |
| `app/api/routes/health.py` | The only extracted router |
| `frontend/index.html` | Entire board — markup, styles and script in one file |
| `tests/conftest.py` | `TestClient` and storage-reset fixtures |
| `Dockerfile` | Multi-stage, non-root runtime image |
| `.github/workflows/ci.yml` | pytest on Python 3.11 |

## 5. Conventions

**Validation** lives in the models, not the routes. Validators raise
`ValueError`; FastAPI converts it to 422. The one exception is the status
transition, which raises `HTTPException` directly from `business_rules.py`
because it needs the stored value to compare against.

**Storage** is three module-level containers. Comments are keyed by task id;
the activity log is a flat list, because entries outlive the tasks they
describe. Derived values are computed on read rather than stored.

**Error handling** is entirely explicit — there is no `except` anywhere in
`app/`. Unknown ids return 404; validation failures return 422. On `PATCH`, the
404 is checked before the transition rule.

**Frontend/backend** are separate processes. The API serves no static files;
CORS allows any localhost origin plus the `null` origin that `file://` sends,
with credentials disabled. All filtering is delegated to the API rather than
duplicated client-side, and every user-supplied string is escaped before being
inserted into the DOM.

## 6. Not visible or assumptions

- `settings` is imported by `app/main.py` but never used, so `PORT` in `.env`
  has no effect — the port comes from the `--port` flag.
- `frontend/index.html` is 2160 lines and was read selectively; claims about it
  cover CORS interaction, escaping and filter delegation only.
- Test *counts* and file names were read, not the assertion bodies.
- No production or deployment behaviour exists to describe.

---

*Written as "Strategy A — minimal context": produced from a one-line task
description plus repo inspection, with no supplied summaries. Caveat on that
framing: this document was written in a session that had already inspected the
same files many times, so it reflects accumulated knowledge rather than a cold
start. A true minimal-context control needs a fresh session.*
