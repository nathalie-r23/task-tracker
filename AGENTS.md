# AGENTS.md

Guidance for AI coding agents working in this repository — a learning-project
Kanban Task Tracker (FastAPI REST API + single-file frontend), currently in
**Module 5: grading and governing AI-assisted work**.

## 1. Project summary

A Kanban task tracker built as a course project. Tasks carry a title,
description, status, priority, assignee, optional due date (with server-computed
overdue state) and tags. Each task has append-only comments and a per-field
activity log. The board supports drag-and-drop between columns, text search and
stacking filters.

Storage is in-process Python dictionaries and is wiped on restart. There is no
database, no authentication, no persistence layer and nothing deployed. The
Docker image and CI workflows build and verify; they do not publish or deploy.

## 2. Tech stack and commands

| Piece | Version | Source |
|---|---|---|
| Python | 3.10.11 local `venv/` · 3.11 in CI and Docker | `.github/workflows/ci.yml`, `Dockerfile` |
| FastAPI | 0.139.0 | `requirements.txt` |
| Pydantic | 2.13.4 (v2 idioms: `ConfigDict`, `field_validator`, `computed_field`) | `requirements.txt`, `app/models.py` |
| pydantic-settings | 2.14.2 | `app/core/config.py` |
| Uvicorn | 0.50.2 (`uvicorn[standard]`) | `requirements.txt` |
| pytest | 9.1.1 | `requirements.txt` |
| httpx | 0.28.1 | transport under `TestClient` |
| Frontend | Vanilla JS, one file, no build step | `frontend/index.html` (2160 lines) |

No `pyproject.toml`, `setup.py`, `setup.cfg`, `pytest.ini` or `tox.ini` exists.
Dependencies are pinned in `requirements.txt` only.

**Run the API:**

```bash
uvicorn app.main:app --reload --port 8000
```

**Serve the frontend** (separate process; the API serves no static files):

```bash
python -m http.server 5500 --directory frontend
```

**Run tests** — 125 collected:

```bash
pytest -v
```

`app/core/config.py` reads `PORT` (default 8000) and `APP_ENV` (default
`development`) from the environment or an optional `.env`. Both have defaults;
the app runs without a `.env`. Note that `PORT` is **not** wired into the uvicorn
command — the port comes from the `--port` flag.

## 3. Business rules visible in the code

**Statuses** (`app/models.py`) — case-sensitive on the wire:
`ToDo` · `InProgress` · `Done`. Default on create: `ToDo`.

**Priorities**: `Low` · `Medium` · `High`. Default: `Medium`.

**Status transitions** (`app/business_rules.py`) — closed allow-list:

| From → To | Allowed |
|---|---|
| `ToDo` → `InProgress` | yes |
| `InProgress` → `Done` | yes |
| `Done` → `InProgress` | yes (reopen) |
| same → same (all three) | yes (no-op) |
| `ToDo` → `Done`, `InProgress` → `ToDo`, `Done` → `ToDo` | **no — 422** |

The check runs **only on `PATCH`**, and only when the body carries a `status`.
`POST /tasks` does not call it, so a task can be *created* directly as `Done`.
On `PATCH`, an unknown id answers 404 before the transition is evaluated.

**Validation** (`app/models.py`):

- `title`: required, trimmed, non-blank, max 200 chars. Explicit `null` on
  `PATCH` is 422.
- `tags`: max 10, each max 24 chars, trimmed, blanks rejected, duplicates
  dropped case-insensitively keeping the first spelling.
- Comment `body`: required, trimmed, max 2000 chars. `author`: optional, max 80
  chars, blank stored as `null`. Comments are append-only.
- All models use `extra="forbid"`, so unknown fields are 422.

**Null-clearing on `PATCH`**: `tags` → `[]`, `description` → `""`, `assignee`
and `due_date` → null, `title` → 422. Omitting a key leaves the field untouched.

**Derived fields**: `is_overdue` is computed on every read, never stored — due
date strictly before today (UTC) **and** status not `Done`. No due date, or due
today, is never overdue. `comment_count` is stamped by the storage layer.

**Activity** (`app/storage.py`): one entry per changed field; kinds are
`created`, `updated`, `commented`, `deleted`. Re-sending a field's current value
records nothing but still bumps `updated_at`; an empty body touches nothing.
Commenting records an entry without bumping `updated_at`. Values are flattened
to text; **only plain strings** are truncated at 80 chars — lists, dates and
enums render untruncated.

**Delete**: removes the task and its comments, keeps its activity, records a
`deleted` entry. `GET /tasks/{id}/activity` then 404s; the history stays on
`GET /activity`, which never 404s (`limit` default 50, max 200).

**Filters** on `GET /tasks` (`status`, `priority`, `overdue`, `tag`, `q`) all
combine with AND. `overdue` is tri-state; `tag` is case-insensitive exact match;
`q` is a case-insensitive literal substring of title or description only.

**CORS** (`app/main.py`): `allow_origins=["null"]` plus a regex for any
localhost/127.0.0.1 port. Credentials are disabled — there is no auth.

## 4. Module 5 guardrails

- **Docs-first.** Write to `docs/` by default. `AGENTS.md` and `CLAUDE.md` may be
  updated when the task is explicitly about agent guidance.
- **Read-only by default.** Inspect and report before proposing an edit. Show
  the proposed content or diff and wait for approval.
- **No `app/` changes** unless the user explicitly approves one specific minimal
  fix. The same applies to `tests/`, `Dockerfile`, `.dockerignore` and
  `.github/workflows/`.
- **One bounded task per thread.** Do not expand scope mid-task. If you find
  something outside the brief, report it and stop.
- **Do not rewrite `docs/midcourse/` deliverables** as a side effect of another
  change.
- **Do not add dependencies** or change pinned versions in `requirements.txt`.
- **Do not change** status-transition rules, the overdue rule, or enum wire
  values — tests and `docs/` depend on them.

## 5. Security and governance

- **Never paste, echo or commit secrets.** `.env` is gitignored and excluded from
  the Docker image; keep it that way. `.env.example` holds only `PORT` and
  `APP_ENV`, neither of which is a secret.
- **No destructive commands** without explicit approval: no `git push --force`,
  no history rewrites, no `rm -rf`, no `git reset --hard`, no dropping or
  overwriting files you have not read.
- **Cite files.** Every claim about this repo must name the file, and a line
  number where it helps. "The code does X" without a path is not acceptable.
- **Do not invent findings.** If a file is not visible, a command was not run, or
  a result was not observed, say so. Mark unconfirmed claims `[VERIFY]` rather
  than asserting them.
- **Verify before claiming.** Behaviour claims — status codes, limits,
  validation outcomes — should be confirmed by running the behaviour, not by
  reading the handler. See `docs/checklists/doc-claim-audit.md`.
- **Never claim** the project has authentication, a database, persistence,
  deployment or production hardening. It has none.

## 6. Known open items

Recorded so an agent does not rediscover them and report them as new:

- Docker **has** been built and run locally (2026-08-15) after WSL was installed;
  the engine had previously refused to start. Four of five checks passed on
  observation. The fifth failed: `.dockerignore` was shipping nested
  `__pycache__` into the image because bare patterns match only top-level
  entries. Fixed with `**/` prefixes. See `docs/module4/docker-security-log.md`.
- Both `.dockerignore` assertions in `.github/workflows/docker-verify.yml` are
  **non-discriminating on a CI runner** — a fresh checkout has no bytecode to
  exclude and none of the other checked paths are ever copied into the runtime
  stage, so both pass regardless of the file's contents. Do not treat them as
  evidence that `.dockerignore` works.
- `tests/verify_a.py` is a tracked print-based script, not a pytest module — it
  defines no `test_` functions, so pytest collects nothing from it.
- The top-level `docs/*.md` files are **deliberate pointers** to the full
  documents in `docs/midcourse/`, not stale duplicates. `docs/README.md`
  explains why. Do not propose deleting either set.
