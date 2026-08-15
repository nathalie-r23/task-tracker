# Docker Security Log

Three required checks: **non-root**, **slim base**, **no baked secrets**.

## Status: VERIFIED LOCALLY — 2026-08-15

The engine would not start for most of this project: every API call returned
`500 Internal Server Error`, because WSL had no distributions installed
(`wsl -l -v` reported none). After WSL was installed the `docker-desktop` distro
came up and the engine responded — `Server: 29.7.2`.

The image was then **built and run on the development machine**. The three
required checks below are **observations**, not claims.

**One check failed.** See §"Finding D1" — bytecode caches shipped into the image.
This was invisible until the build actually ran, and it is invisible in CI for
the reason given there.

**Image:** `task-tracker:dev` · built from `Dockerfile` at commit `9a86a43`
**Size:** `docker images` reports **293MB**; `docker image inspect .Size` reports
**68,747,439 bytes (~65.6MB)**. The two disagree because the build produced an
attestation manifest list; the 293MB figure is the on-disk uncompressed total.
Both are recorded rather than choosing one.
**Port note:** mapped `-p 8001:8000` because port 8000 was occupied by a local
uvicorn — the exact clash `README.md` warns about. All `curl` checks below used
8001 accordingly.

## The log

| Check | Result | Observed evidence |
|---|---|---|
| **Non-root** | **PASS** | `docker exec tt-dev whoami` → `app`. `docker exec tt-dev id` → `uid=1000(app) gid=1000(app) groups=1000(app)`. Image config: `user=app` |
| **Slim base** | **PASS** | `docker image inspect` → `cmd=["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]`, `ports={"8000/tcp":{}}`. No `--reload`. Built from `python:3.11-slim` in both stages; pip and build tooling confined to the discarded builder |
| **No baked secrets** | **PASS** | All thirteen checked paths absent from `/app`: `.env`, `.git`, `.github`, `venv`, `.venv`, `tests`, `frontend`, `docs`, `requirements.txt`, `.pytest_cache`, `README.md`, `CLAUDE.md`, `AGENTS.md`. Positive control passed — `/app/app/main.py` and `/app/app/business_rules.py` both present, so the absences are real, not an empty image |
| **Health served** | **PASS** | Via published port: `curl http://localhost:8001/health` → `{"status":"ok","timestamp":"2026-08-15T15:44:08.560475+00:00"}`, responding within 1s. From inside the container: `docker exec tt-dev python -c "...urlopen('http://127.0.0.1:8000/health')"` → same shape, confirming uvicorn bound `0.0.0.0` rather than a host process answering |
| **No bytecode shipped** | **PASS** (after fix) | Initially failed; see Finding D1. After the two-line `.dockerignore` fix and a rebuild, `find /app -name '__pycache__' -o -name '*.pyc'` returns empty, while `/app/app/main.py`, `business_rules.py`, `schemas/health.py` and the rest remain present |

## Finding D1 — `.dockerignore` did not exclude nested `__pycache__` — RESOLVED

**Severity: Low** (no secret exposure; stale bytecode and wasted image layers)
**Status: fixed and verified 2026-08-15**

Ten bytecode entries shipped into the image:

```
/app/app/__pycache__/            /app/app/api/__pycache__/
/app/app/api/routes/__pycache__/ ... including storage, models,
health and a stale tasks.cpython-310.pyc
```

**Root cause.** `.dockerignore:16` is a bare `__pycache__`, and `:17` a bare
`*.py[cod]`. Docker matches ignore patterns against the path relative to the
build-context root, so a bare pattern matches **only a top-level entry**. There
is no top-level `__pycache__` in this repo — every cache is nested under `app/`,
so nothing matched and `COPY app ./app` (`Dockerfile:41`) copied them all.

**Why CI never caught it.** `docker-verify.yml` has an "Assert no bytecode caches
shipped" step, and this document previously described it as the check that
genuinely exercises `.dockerignore`. That was half right. On a GitHub runner,
`actions/checkout` produces a fresh tree with **no `__pycache__` at all** — git
does not track it — so the step passes because there is nothing to exclude, not
because exclusion works. **Both** `.dockerignore` assertions in that workflow are
therefore non-discriminating in CI, and the defect only appears on a developer
machine that has run the test suite.

**Aggravating detail.** The shipped files are `cpython-310` bytecode from the
local 3.10 venv, inside an image running Python 3.11. Python ignores bytecode
with a mismatched magic number, so it is inert — but it is dead weight built from
a different interpreter. One entry, `tasks.cpython-310.pyc`, is a cache for a
route module that no longer exists in `app/api/routes/`.

**Fix — APPLIED, with approval.** Two lines in `.dockerignore`:

| Current | Fixed |
|---|---|
| `__pycache__` | `**/__pycache__` |
| `*.py[cod]` | `**/*.py[cod]` |

A comment above them records why the `**/` prefix is load-bearing, so the
pattern is not "simplified" back later.

**Verification after the rebuild — all on the same machine that has run the test
suite, so the caches genuinely existed in the build context:**

| Check | Before | After |
|---|---|---|
| `find /app -name '__pycache__' -o -name '*.pyc'` | 10 entries | **empty** |
| Positive control — `.py` sources present | pass | pass (`main.py`, `business_rules.py`, `schemas/health.py`, both `routes/` files) |
| `/health` via published port | 200 | **200** |
| `/health` from inside container | 200 | **200** |
| `whoami` / `id` | `app` / uid=1000 | **`app` / uid=1000** |
| 13 excluded paths absent | pass | **pass** |
| `inspect .Size` | 68,747,439 bytes | **68,732,880 bytes** |

Size fell by **14,559 bytes** — small, which is itself the honest result: the
defect was about shipping stale artifacts from the wrong interpreter, not about
image bloat. Nothing else changed.
| **Slim base** | `python:3.11-slim` pinned for both builder and runtime; no `python:latest`; pip, its cache and build tooling stay in the discarded builder stage | `Dockerfile:6,24`; `PIP_NO_CACHE_DIR=1` at `:9` | Build log showing both `FROM` lines; `docker image inspect task-tracker:dev --format '{{.Size}}'` |
| **No baked secrets** | `.env*` excluded via `.dockerignore`; no `ARG`/`ENV` carries a credential; configuration is supplied at runtime through environment variables | `.dockerignore:8`; the only `ENV`s are `PATH`, `PYTHONUNBUFFERED`, `PYTHONDONTWRITEBYTECODE`, `PIP_*` | Output of the "only the app package shipped" step showing `absent: .env` |

## Commands to produce the evidence

Start the Docker Desktop GUI first and wait for the engine to report running.

```bash
docker build -t task-tracker:dev .
```

```bash
docker run -d --name tt-dev -p 8000:8000 task-tracker:dev
```

```bash
curl http://localhost:8000/health
```

```bash
docker exec tt-dev python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
```

```bash
docker exec tt-dev whoami && docker exec tt-dev id
```

```bash
docker image inspect task-tracker:dev --format 'user={{.Config.User}} cmd={{json .Config.Cmd}} ports={{json .Config.ExposedPorts}} size={{.Size}}'
```

```bash
docker run --rm task-tracker:dev sh -c 'for p in .env .git .github venv .venv tests frontend docs .pytest_cache requirements.txt; do if [ -e "/app/$p" ]; then echo "LEAKED: $p"; else echo "absent: $p"; fi; done'
```

```bash
docker rm -f tt-dev
```

If the port is already taken by a local uvicorn, use `-p 8001:8000` **and change
the `curl` port to match** — otherwise you are testing the local server, not the
container.

## Note on the exclusion check

The last command proves that only the `app` package shipped. It does **not**
prove `.dockerignore` is working: the runtime stage copies only `app/`, so those
paths would be absent regardless. The check that genuinely exercises
`.dockerignore` is the bytecode assertion in `docker-verify.yml` — `__pycache__`
lives *inside* `app/` in any working copy that has run the suite, so it reaches
the build context and is excluded only because `.dockerignore` says so.

## Alternative evidence source

If the local engine cannot be started, `docker-verify.yml` runs every check above
on a GitHub runner and prints an "Evidence summary" step with image layers,
container status and application logs. A link to a successful run of that
workflow is acceptable evidence in place of local output — note in the
submission that the evidence is from CI, not from the development machine.
