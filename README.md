# Task Tracker

A learning-project Kanban task tracker: a REST API built with Python, FastAPI and
Pydantic v2, plus a dependency-free single-file frontend.

Tasks have a title, description, status, priority, assignee, an optional **due
date** (with server-computed overdue state) and **tags**, and they carry
**comments** and a per-field **activity log**. The board supports drag-and-drop
between columns, full-text **search**, and stacking filters for priority, tag and
overdue state.

Storage is in-process Python dictionaries. There is no database, no
authentication and no deployment configuration — see
[Conventions and limitations](#conventions-and-current-limitations).

## Final Project

Branch reviewed: `final-project`

### What this submission demonstrates

- The existing Task Tracker still runs inside the intended course scope — no
  product feature was added.
- CI runs the pytest suite on push and pull request, with no
  `continue-on-error`, no `|| true`, and no skipped pytest.
- The Docker image builds and runs, with `/health` returning 200 both through
  the published port and from inside the container, as a non-root user.
- AI review, security and ownership evidence lives in `docs/`.

### How to run locally

```bash
python -m venv venv
```

```bash
venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

```bash
uvicorn app.main:app --reload --port 8000
```

Then serve the frontend separately:

```bash
python -m http.server 5500 --directory frontend
```

### How to run tests

```bash
pytest -v
```

125 tests, all passing.

### How to run with Docker

```bash
docker build -t task-tracker:final .
```

```bash
docker run -d --name tt-final -p 8000:8000 task-tracker:final
```

```bash
curl http://localhost:8000/health
```

If port 8000 is already taken by a local uvicorn, map a different host port
(`-p 8001:8000`) **and** change the port in the `curl` to match — otherwise you
are testing the local server rather than the container.

### Evidence files

- [docs/release-evidence.md](docs/release-evidence.md)
- [docs/final-ai-review.md](docs/final-ai-review.md)
- [docs/ai-playbook.md](docs/ai-playbook.md)

### AI assistance summary

AI helped draft or review: CI workflows, the Dockerfile and `.dockerignore`,
docstrings and README, a security review, and debugging.

I verified the work by: running the full pytest suite, building and running the
container and checking `/health` from inside it, querying `/openapi.json` and
the live endpoints rather than reading the handlers, and grading every AI
finding as Valid, False Positive or Noise.

One AI suggestion I rejected or corrected: a review claimed the top-level
`docs/*.md` files were superseded stubs and suggested deleting a set. They are
deliberate pointers to `docs/midcourse/`, as `docs/README.md` states — acting on
it would have deleted a graded deliverable. Recorded in
[docs/final-ai-review.md](docs/final-ai-review.md).

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | **3.11** | What CI and the Docker image use. CI verified green — [run #14](https://github.com/nathalie-r23/task-tracker/actions/runs/31905311907); the image was built and run locally on 2026-08-15 |
| Python (local dev) | 3.10.11 | The checked-in `venv/` — the suite passes on this too |
| Docker | any recent | **Optional**, only for the container workflow |

The 3.11 pin is not enforced by any config file in this repo; it is set in
`.github/workflows/ci.yml` and the `Dockerfile`. Older interpreters are
untested — the previous "Python 3.9+" claim was never verified and has been
dropped. **[VERIFY]** if you need a supported floor below 3.10.

## Local setup

From the repository root:

```bash
python -m venv venv
```

```bash
venv\Scripts\activate
```

On macOS or Linux use `source venv/bin/activate` instead.

```bash
pip install -r requirements.txt
```

Optional configuration lives in `.env` (see `.env.example`). Both settings have
defaults, so the app runs without it:

```
PORT=8000
APP_ENV=development
```

## Run the app locally

Two servers, two terminals. Backend first:

```bash
uvicorn app.main:app --reload --port 8000
```

- API: <http://localhost:8000>
- Interactive docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Then serve the frontend on any local port:

```bash
python -m http.server 5500 --directory frontend
```

Open <http://localhost:5500>. Opening `frontend/index.html` straight from disk
also works — CORS accepts any `localhost` origin plus the `null` origin that
`file://` sends.

Tasks are cleared whenever the server restarts.

## Run tests

```bash
pytest -v
```

**125 tests** covering CRUD, validation, status-transition rules, null-clearing
semantics, due dates and overdue state, tags and tag filtering, text search,
comments, and the activity log.

## Run with Docker

The image is multi-stage on `python:3.11-slim` and runs as a non-root `app`
user. From the repository root:

```bash
docker build -t task-tracker:dev .
```

```bash
docker run -d --name tt-dev -p 8000:8000 task-tracker:dev
```

If port 8000 is already taken by a local uvicorn, use `-p 8001:8000` instead —
and change the port in the `curl` below to match, or you will be checking the
local server rather than the container.

```bash
curl http://localhost:8000/health
```

```bash
docker exec tt-dev whoami
```

That last command prints `app`, confirming the container is not running as
root. Remove the container with `docker rm -f tt-dev`.

The image contains only the interpreter, the installed dependencies and
`app/`. Tests, the frontend, `docs/`, `.env` and git metadata are excluded by
`.dockerignore`. Built and run locally on 2026-08-15: `docker images` reports
**293MB** (`docker image inspect .Size` reports 68,732,880 bytes — the two differ
because the build produces an attestation manifest list). All five security
checks pass on observation; see
[docker-security-log.md](docs/module4/docker-security-log.md).

## CI workflow summary

Two workflows, neither of which deploys anything.

| Workflow | Trigger | What it does |
|---|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | every `push` and `pull_request` | Checks out, sets up Python 3.11, installs from `requirements.txt`, runs `pytest -v` |
| [`docker-verify.yml`](.github/workflows/docker-verify.yml) | `push`/`pull_request` touching `Dockerfile`, `.dockerignore`, `requirements.txt` or `app/**`, plus manual dispatch | Builds the image, starts the container, checks `/health` through the port mapping and from inside, asserts the user is `app`, asserts only the `app` package shipped, and asserts no bytecode caches reached the image (the step that actually exercises `.dockerignore`) |

Neither workflow uses `continue-on-error`, `|| true` or `--exit-zero`, and
pytest output is not piped, so a failing test fails the check. This was proved
by deliberately breaking one assertion and confirming CI turned red, then
restoring it.

## Project structure

```
app/
  main.py            FastAPI app, routes, CORS
  models.py          Pydantic models, validation, overdue rule, activity values
  storage.py         In-memory stores, filtering, activity recording
  business_rules.py  Status-transition rules
  core/config.py     Settings loaded from .env
  api/routes/        Health router
  schemas/           Health response schema
frontend/
  index.html         Kanban board (no build step, no dependencies)
tests/
  conftest.py        TestClient + storage-reset fixtures
  test_tasks.py      Task CRUD, filters, due dates, tags, search
  test_comments.py   Comment CRUD, validation, comment_count
  test_activity.py   Activity entries, value formatting, delete events, feed
  test_health.py     Health endpoint
.github/workflows/
  ci.yml             Test suite on Python 3.11
  docker-verify.yml  Image build and runtime verification
Dockerfile           Multi-stage, non-root runtime image
docs/                Project documentation (see below)
CLAUDE.md            Working notes for Claude Code sessions
```

## API

| Method | Endpoint | Notes |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/tasks` | Optional filters: `status`, `priority`, `overdue`, `tag`, `q` — all combine with AND |
| `POST` | `/tasks` | Create a task; `201` on success |
| `GET` | `/tasks/{id}` | `404` if unknown |
| `PATCH` | `/tasks/{id}` | Partial update; only the fields sent are changed |
| `DELETE` | `/tasks/{id}` | `204`; removes the task's comments, keeps its activity, records a `deleted` event |
| `GET` | `/tasks/{id}/comments` | Comments, oldest first; `404` if the task is unknown |
| `POST` | `/tasks/{id}/comments` | Add a comment; `201` on success |
| `GET` | `/tasks/{id}/activity` | One task's history, newest first; `404` if the task is unknown |
| `GET` | `/activity` | Board-wide feed, newest first. Filters: `kind`, `task_id`, `limit` (default 50, max 200) |

### Filters

| Param | Type | Notes |
|---|---|---|
| `status` | enum | Exact match |
| `priority` | enum | Exact match |
| `overdue` | bool | Tri-state: omitted = all, `true` = only overdue, `false` = only the rest |
| `tag` | string | Case-insensitive exact match against any one tag |
| `q` | string | Case-insensitive **literal substring** of title or description. Trimmed; blank means no filter. Does not match assignee or tags. |

### Task fields

| Field | Type | Notes |
|---|---|---|
| `id` | string | UUID, server-assigned |
| `title` | string | Required, trimmed, max 200 chars. On `PATCH`, an explicit `null` is `422` — there is nothing to clear it to |
| `description` | string | Defaults to `""`; send `null` to clear it back to `""` |
| `status` | enum | `ToDo` · `InProgress` · `Done` — case-sensitive on the wire |
| `priority` | enum | `Low` · `Medium` · `High` |
| `assignee` | string \| null | Optional |
| `due_date` | date \| null | ISO `YYYY-MM-DD`; send `null` to clear |
| `tags` | string[] | Max 10, each max 24 chars, trimmed, deduplicated case-insensitively |
| `is_overdue` | bool | **Read-only, computed** — due date in the past and status is not `Done` |
| `comment_count` | int | **Read-only, derived** from the comment store on every read |
| `created_at` / `updated_at` | datetime | UTC, server-assigned |

### Examples

```bash
curl -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Ship release notes","priority":"High","due_date":"2026-08-14","tags":["backend","urgent"]}'
```

```bash
curl "http://localhost:8000/tasks?q=migration&tag=backend&overdue=true"
```

```bash
curl "http://localhost:8000/activity?kind=deleted"
```

## Conventions and current limitations

**Conventions**

- **Status transitions** are a closed allow-list in `app/business_rules.py`:
  `ToDo → InProgress`, `InProgress → Done`, `Done → InProgress`, plus
  same-status no-ops. Anything else returns `422`. The check runs **only on
  `PATCH`** — `POST /tasks` does not call it, so a task can be *created*
  directly as `Done`.
- **Overdue** is derived on every read, never stored, so a task becomes overdue
  when the date rolls over. Due *today* is not overdue, and a `Done` task is
  never overdue.
- **Activity** is recorded per changed field. Re-sending a field's current value
  records no entry, though it does still refresh `updated_at`. A body with no
  fields at all leaves `updated_at` untouched. Commenting records an entry but
  does not change `updated_at`.
- **Comments are append-only** — no edit, no delete.
- Enum wire values are **case-sensitive**; `todo` is rejected, `ToDo` is not.

**Current limitations**

- **Storage is in-memory.** Everything is lost on restart. There is no database
  and no persistence layer.
- **No authentication or authorization.** No users, sessions or tokens. CORS is
  configured on that assumption, with credentials disabled.
- **Not deployed and not production-hardened.** The Docker image is built and
  verified in CI but is not published to a registry or hosted anywhere.
- **The frontend is not served by the API.** It is a separate static file, and
  `API_BASE` is hardcoded to `http://localhost:8000`.
- Single-process only; no concurrency control beyond what one Uvicorn worker
  gives you.

## Documentation

Mid-course project documentation lives in [`docs/`](docs/README.md):

- [user-stories.md](docs/midcourse/user-stories.md) — stories and acceptance criteria
- [mini-adr.md](docs/midcourse/mini-adr.md) — design decisions and rejected alternatives
- [prompt-log.md](docs/midcourse/prompt-log.md) — prompts, and what was accepted, edited or rejected
- [verification.md](docs/midcourse/verification.md) — baseline, test results, manual checks, Break Tests
- [reflection.md](docs/midcourse/reflection.md) — reflection on the AI-assisted workflow

Each of these five also exists as a short pointer file at the top level of
`docs/` — deliberate, not duplication: the course brief names both locations,
so the full documents live in `docs/midcourse/` and the top-level copies
summarise and link to them. See [docs/README.md](docs/README.md) for the
mapping. Keep both.

Standalone technical notes live in [`docs/decisions/`](docs/decisions/):

- [0001-documentation-verification.md](docs/decisions/0001-documentation-verification.md)
  — how documentation claims are verified before publishing (**draft**)

The broader design record remains [mini-adr.md](docs/midcourse/mini-adr.md).
