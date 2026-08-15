# CLAUDE.md

Guidance for Claude Code when working in this repository — a Module 4 learning-project
Kanban Task Tracker (REST API + single-file frontend).

## 1. Tech stack

| Piece | Version | Notes |
|---|---|---|
| Python | 3.10.11 local / 3.11 CI | Local `venv/` is 3.10.11 and the suite passes on it. CI (`.github/workflows/ci.yml`) and the `Dockerfile` both pin 3.11. No config file enforces a floor. |
| FastAPI | 0.139.0 | Pinned in `requirements.txt` |
| Pydantic | v2 (2.13.4) | v2 idioms throughout: `ConfigDict`, `field_validator`, `computed_field` |
| pydantic-settings | 2.14.2 | Backs `app/core/config.py` |
| python-dotenv | 1.2.2 | Optional `.env` (see `.env.example`) |
| Uvicorn | 0.50.2 (`uvicorn[standard]`) | ASGI server |
| pytest | 9.1.1 | Test runner |
| httpx | 0.28.1 | Transport under `fastapi.testclient.TestClient` |
| Frontend | Vanilla JavaScript | `frontend/index.html` — one file, no build step, no dependencies, no framework |

There is no database, no ORM, no auth layer, and no build tooling. Storage is in-process
Python dicts and is wiped on restart.

## 2. Run command

```bash
uvicorn app.main:app --reload --port 8000
```

- API: <http://localhost:8000>
- Docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

The frontend is served separately as static files:

```bash
python -m http.server 5500 --directory frontend
```

## 3. Test command

```bash
pytest -v
```

## 4. Architecture

### Backend (`app/`)

| File | Responsibility |
|---|---|
| `main.py` | `create_app()`, CORS middleware, and every task/comment/activity route |
| `models.py` | Pydantic models, field validation, the overdue rule, activity-value flattening |
| `storage.py` | In-memory stores, filtering, activity recording, `MAX_ACTIVITY_LIMIT`/`DEFAULT_ACTIVITY_LIMIT` |
| `business_rules.py` | **Status-transition rules live here** — `VALID_TRANSITIONS` + `validate_status_transition()` |
| `core/config.py` | Settings loaded from `.env` |
| `api/routes/health.py` | Health router (the only extracted router; task routes are still in `main.py`) |
| `schemas/health.py` | Health response schema |

### Frontend (`frontend/`)

- `index.html` — the whole board: markup, `<style>`, and `<script>` in one file.
  `API_BASE` is hardcoded to `http://localhost:8000`.

### Tests (`tests/`)

- `conftest.py` — `TestClient` + storage-reset fixtures
- `test_tasks.py` — CRUD, filters, due dates, tags, search
- `test_comments.py` — comment CRUD, validation, `comment_count`
- `test_activity.py` — activity entries, value formatting, delete events, board feed
- `test_health.py` — health endpoint

### Where the rules live

- **Status transitions** → `app/business_rules.py`
- **Field validation** (title, tags, comment body/author) → `app/models.py`
- **Overdue** → `compute_is_overdue()` in `app/models.py`
- **Filtering / activity recording** → `app/storage.py`
- Design rationale → `docs/midcourse/mini-adr.md`

## 5. Business rules

### Status values

`TaskStatus` (`app/models.py`) is a string enum with exactly three values, and the
wire format is case-sensitive:

- `ToDo`
- `InProgress`
- `Done`

Default on create: `ToDo`. (`TaskPriority` is `Low` / `Medium` / `High`, default `Medium`.)

### Transition rules

`VALID_TRANSITIONS` in `app/business_rules.py` is a closed allow-list:

| From | To | Allowed |
|---|---|---|
| `ToDo` | `InProgress` | yes |
| `InProgress` | `Done` | yes |
| `Done` | `InProgress` | yes (reopen) |
| `ToDo` → `ToDo`, `InProgress` → `InProgress`, `Done` → `Done` | | yes (no-op) |
| `ToDo` | `Done` | **no** |
| `InProgress` | `ToDo` | **no** |
| `Done` | `ToDo` | **no** |

Anything outside the list raises `HTTPException` with **422**, with a detail listing the
allowed transitions.

Two details that are easy to get wrong:

- The check runs **only on `PATCH /tasks/{id}`**, and only when the payload contains a
  `status`. `POST /tasks` does **not** call `validate_status_transition`, so a task can be
  *created* directly as `Done` — the rule constrains movement, not the starting point.
- On `PATCH`, the 404-vs-422 order matters: an unknown id 404s before the transition is
  evaluated.

### Other enforced rules

- `title`: required, trimmed, non-blank, max 200 chars. On `PATCH`, an explicit
  `"title": null` is **422** — a required field has nothing to clear to.
- `tags`: max 10 tags, each max 24 chars, trimmed, blanks rejected, duplicates dropped
  case-insensitively keeping the first spelling. On `PATCH`, an explicit `"tags": null`
  clears them to `[]`.
- Null-clearing on `PATCH`, in one place: `tags` → `[]`, `description` → `""`,
  `assignee` and `due_date` → null, `title` → 422. Omitting a key always leaves that
  field untouched.
- `is_overdue`: computed on every read, never stored — `due_date` strictly before today
  (UTC) **and** status is not `Done`. No due date → never overdue. Due *today* → not overdue.
- `comment_count`: read-only, stamped by the storage layer from the live comment store.
- Comments: `body` required, trimmed, max 2000 chars; `author` optional, max 80 chars, blank
  stored as `null`. Append-only — no edit, no delete.
- Activity: one entry per changed field; kinds are `created`, `updated`, `commented`,
  `deleted`. Re-sending a field's current value records nothing. Commenting records an entry
  but does **not** bump `updated_at`. Values are flattened to text; only plain strings
  are truncated at 80 chars — enums, dates and tag lists render untruncated, so a full
  tag list can exceed it. `task_title` is a snapshot from the time of the event, not a
  live lookup.
- Delete: removes the task's comments, **keeps** its activity, records a `deleted` entry.
  `GET /tasks/{id}/activity` then 404s; the history stays readable on `GET /activity`.
- `GET /activity`: `limit` defaults to 50, capped at 200; never 404s (it is a log, not a
  sub-resource) — an unknown `task_id` returns `[]`.
- All `GET /tasks` filters (`status`, `priority`, `overdue`, `tag`, `q`) combine with AND.
  `overdue` is tri-state; `tag` is case-insensitive exact match; `q` is a case-insensitive
  literal substring of title or description only.

## 6. UI states and CORS

### CORS (`app/main.py`)

```python
allow_origins=["null"]                                          # file:// pages
allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"  # any local port
allow_methods=["*"], allow_headers=["*"], allow_credentials=False
```

So the board works both when served from a local static server (5500, 5173, whatever) and
when `frontend/index.html` is opened straight from disk. Credentials are off deliberately —
there is no auth.

### Board states (`boardState` in `frontend/index.html`)

- `loading` — skeleton placeholders in each column
- `error` — full-width card: "Unable to load tasks. Please try again later."
- `ready` — the three columns render; an empty column shows a "Drop tasks here" drop zone

Additional states:

- Failed drag-and-drop `PATCH` reverts the card and shows a `board-message error` banner
  carrying the server's `detail` (this is how a rejected 422 transition surfaces).
- Modals: per-field `field-error` spans plus a `form-error` banner (`role="alert"`).
- Detail modal empties: "No comments yet.", "Nothing recorded yet.", "Nothing has happened
  yet.", and "Unable to load activity." on a failed fetch.
- Modals set `aria-hidden`, lock body scroll, and close on Escape / the × button.
- Task titles are escaped before injection — a title like `<img onerror=...>` must not execute.

## 7. Do not

Do not do any of the following without asking first:

- **Add authentication or authorization** — no users, sessions, tokens, or login. There is
  none by design, and CORS is configured on that assumption.
- **Add a database or any persistence layer** — storage is intentionally in-memory and
  resets on restart. No SQLAlchemy, no SQLite, no file-backed store.
- **Add hosting or deployment steps** — no registry pushes, hosting config, or
  production settings. Docker and GitHub Actions *are* now in scope (`Dockerfile`,
  `.dockerignore`, `.github/workflows/`), but strictly to build, test and verify
  locally and on CI runners. Nothing is published or deployed anywhere.
- **Make major UI changes** — no framework, no build step, no splitting `index.html` apart,
  no redesign. Small, contained edits within the existing file only.

Also:

- Do not add dependencies beyond `requirements.txt`, or unpin/bump the pinned versions.
- Do not change the status-transition rules, the overdue rule, or the enum wire values —
  tests and `docs/midcourse/` depend on them.
- Do not rewrite `docs/midcourse/` deliverables (user stories, mini-ADR, prompt log,
  verification, reflection) as a side effect of a code change.
