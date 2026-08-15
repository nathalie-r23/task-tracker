# Task Tracker — Architecture (structured context)

*Written from `AGENTS.md` and the file listing in `README.md`. Source-code
internals were not inspected; claims trace to those two documents.*

## 1. What the app does

A Kanban task tracker: a FastAPI REST API plus a single-file vanilla-JavaScript
frontend. Tasks carry a title, description, status, priority, assignee, optional
due date with server-computed overdue state, and tags; each has append-only
comments and a per-field activity log. The board supports drag-and-drop between
columns, text search and stacking filters. Storage is in-process Python
dictionaries, wiped on restart. No database, no authentication, nothing deployed
— the Docker image and CI workflows build and verify only.

## 2. Data model

**Task** — title (required, trimmed, non-blank, ≤200 chars), description, status,
priority, assignee, due date, tags (≤10, each ≤24 chars, trimmed, blanks
rejected, duplicates dropped case-insensitively keeping the first spelling).
Statuses are `ToDo` · `InProgress` · `Done`, case-sensitive on the wire, default
`ToDo`. Priorities are `Low` · `Medium` · `High`, default `Medium`.

Two derived fields are never stored: `is_overdue`, computed on every read as due
date strictly before today in UTC **and** status not `Done` — no due date, or
due today, is never overdue; and `comment_count`, stamped by the storage layer.

**Comment** — body (required, trimmed, ≤2000 chars), author (optional, ≤80
chars, blank stored as null). Append-only: no edit, no delete.

**Activity entry** — one per changed field. Kinds are `created`, `updated`,
`commented`, `deleted`. Values are flattened to text; only plain strings are
truncated at 80 chars, so a full tag list can exceed it. The task title is a
snapshot from the time of the event, not a live lookup.

## 3. Request flow — creating a task

`POST /tasks` validates the body: title is required and trimmed, tags are
normalised, and unknown fields are rejected with 422 because all models use
`extra="forbid"`. Status defaults to `ToDo` and priority to `Medium`.

The status-transition allow-list is **not** applied on create — `AGENTS.md`
states the check runs only on `PATCH`, so a task may be created directly as
`Done`. The rule constrains movement, not the starting point. A `created`
activity entry is recorded.

The exact internal sequence — id generation, timestamp assignment, the order of
storage write versus activity write — is not described in the context I was
given.

## 4. Key files

| File | Role |
|---|---|
| `app/main.py` | FastAPI app, routes, CORS |
| `app/models.py` | Pydantic models, validation, overdue rule, activity values |
| `app/storage.py` | In-memory stores, filtering, activity recording |
| `app/business_rules.py` | Status-transition rules |
| `app/core/config.py` | Settings loaded from `.env` |
| `app/api/routes/health.py` | Health router — the only extracted router |
| `frontend/index.html` | Kanban board; no build step, no dependencies |
| `tests/conftest.py` | TestClient and storage-reset fixtures |
| `Dockerfile` | Multi-stage, non-root runtime image |
| `.github/workflows/ci.yml` | Test suite on Python 3.11 |

## 5. Conventions

**Validation.** Field rules live in `app/models.py`; status transitions live in
`app/business_rules.py` as a closed six-member allow-list — `ToDo→InProgress`,
`InProgress→Done`, `Done→InProgress`, plus same-status no-ops. Anything else is
422. On `PATCH`, an unknown id answers 404 before the transition is evaluated.

**Null-clearing on `PATCH`** is uniform: `tags`→`[]`, `description`→`""`,
`assignee` and `due_date`→null, `title`→422 because a required field has nothing
to clear to. Omitting a key leaves the field untouched.

**Storage** is in-process dictionaries. Deleting a task removes its comments but
keeps its activity, recording a `deleted` entry; the per-task activity route then
404s while the board-wide feed still shows the history. `GET /activity` never
404s — it is a log, not a sub-resource — and caps `limit` at 200, default 50.

**Error handling.** 422 for validation and rejected transitions, 404 for unknown
ids. All `GET /tasks` filters combine with AND.

**Frontend/backend.** Separate processes; the API serves no static files. CORS
allows the `null` origin plus any localhost/127.0.0.1 port, with credentials
disabled because there is no auth.

## 6. Not visible or assumptions

- Source code was not inspected. Every statement above traces to `AGENTS.md` or
  the `README.md` file listing, both of which could be stale relative to the code.
- The internal create-task sequence (§3) is not described in the context given.
- Model and function names are not given in the context, so none are cited.
- `AGENTS.md` records three open items I could not confirm independently:
  `tests/verify_a.py` is a print-based script rather than a pytest module; the
  top-level `docs/*.md` files are deliberate pointers, not duplicates; and Docker
  claims rested on CI rather than a local run at the time it was written.

---

*Strategy B — structured context: written from `AGENTS.md` plus the README file
listing, with no source files opened. The trade is visible in §3: summaries
document rules exhaustively and mechanics not at all, so the request flow is the
weakest section of the three strategy documents.*
