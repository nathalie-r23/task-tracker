# Task Tracker

A learning-project Kanban task tracker: a REST API built with Python, FastAPI and
Pydantic, plus a dependency-free single-file frontend.

Tasks have a title, description, status, priority, assignee, an optional **due
date** (with server-computed overdue state) and **tags**. The board supports
drag-and-drop between columns and filtering by overdue state and tag.

## Requirements

- Python 3.9+ (developed against 3.10)

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Optional configuration lives in `.env` (see `.env.example`):

```
PORT=8000
APP_ENV=development
```

## Run the backend

```bash
uvicorn app.main:app --reload --port 8000
```

- API: <http://localhost:8000>
- Interactive docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Storage is in memory, so tasks are cleared whenever the server restarts.

## Open the frontend

The frontend is a single static file that calls the API at `http://localhost:8000`.
Start the backend first, then serve `frontend/` on any local port:

```bash
python -m http.server 5500 --directory frontend
```

Then open <http://localhost:5500>. Opening `frontend/index.html` directly from
disk also works — CORS accepts any `localhost` origin plus the `null` origin used
by `file://`.

## Run the tests

```bash
pytest -q
```

57 tests covering CRUD, validation, status-transition rules, due dates / overdue
state, and tags / tag filtering.

## API

| Method | Endpoint | Notes |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/tasks` | Optional filters: `status`, `priority`, `overdue`, `tag` — all combine with AND |
| `POST` | `/tasks` | Create a task; `201` on success |
| `GET` | `/tasks/{id}` | `404` if unknown |
| `PATCH` | `/tasks/{id}` | Partial update; only the fields sent are changed |
| `DELETE` | `/tasks/{id}` | `204` on success |

### Task fields

| Field | Type | Notes |
|---|---|---|
| `id` | string | UUID, server-assigned |
| `title` | string | Required, trimmed, max 200 chars |
| `description` | string | Defaults to `""` |
| `status` | enum | `ToDo` · `InProgress` · `Done` |
| `priority` | enum | `Low` · `Medium` · `High` |
| `assignee` | string \| null | Optional |
| `due_date` | date \| null | ISO `YYYY-MM-DD`; send `null` to clear |
| `tags` | string[] | Max 10, each max 24 chars, trimmed, deduplicated case-insensitively |
| `is_overdue` | bool | **Read-only, computed** — due date in the past and status is not `Done` |
| `created_at` / `updated_at` | datetime | UTC, server-assigned |

**Status transitions** are restricted: `ToDo → InProgress`, `InProgress → Done`,
`Done → InProgress`, and same-status no-ops. Anything else returns `422`.

**Overdue** is derived on every read rather than stored, so a task becomes overdue
when the date rolls over without needing to be written to. A task due *today* is
not overdue, and a `Done` task is never overdue.

### Examples

```bash
# create a task with a due date and tags
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Ship release notes","priority":"High",
       "due_date":"2026-08-14","tags":["backend","urgent"]}'

# only overdue tasks, in one tag
curl "http://localhost:8000/tasks?overdue=true&tag=backend"

# clear a due date
curl -X PATCH http://localhost:8000/tasks/<id> \
  -H "Content-Type: application/json" -d '{"due_date":null}'
```

## Project structure

```
app/
  main.py            FastAPI app, routes, CORS
  models.py          Pydantic models, validation, overdue rule
  storage.py         In-memory store and filtering
  business_rules.py  Status-transition rules
  core/config.py     Settings loaded from .env
  api/routes/        Health router
frontend/
  index.html         Kanban board (no build step, no dependencies)
tests/
  conftest.py        TestClient + storage-reset fixtures
  test_tasks.py      Task CRUD, filters, due dates, tags
  test_health.py     Health endpoint
docs/midcourse/      Mid-course project documentation
```

## Mid-course project documentation

- [user-stories.md](docs/midcourse/user-stories.md) — stories and acceptance criteria
- [mini-adr.md](docs/midcourse/mini-adr.md) — design decisions and rejected alternatives
- [prompt-log.md](docs/midcourse/prompt-log.md) — prompts, and what was accepted, edited or rejected
- [verification.md](docs/midcourse/verification.md) — baseline, test results, manual checks, Break Tests
- [reflection.md](docs/midcourse/reflection.md) — reflection on the AI-assisted workflow
