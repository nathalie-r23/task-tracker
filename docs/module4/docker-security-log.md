# Docker Security Log

Three required checks: **non-root**, **slim base**, **no baked secrets**.

## Status: UNVERIFIED LOCALLY — [VERIFY]

Docker Desktop is installed on the development machine but the engine would not
start: every API call returned `500 Internal Server Error` over roughly 25
minutes, and `%LOCALAPPDATA%\Docker\wsl` does not exist, which points at
incomplete first-run WSL setup. **No image has been built or run locally.**

The three statements below are written from the `Dockerfile` and `.dockerignore`
as committed, and from the assertions in
[`docker-verify.yml`](../../.github/workflows/docker-verify.yml). They are
**claims pending evidence**, not observations. Fill in the evidence column from a
real run before submitting.

## The log

| Check | Claim | Basis today | Evidence to attach |
|---|---|---|---|
| **Non-root** | Runs as `app` (uid 1000, gid 1000); `USER app` precedes `CMD`; the container owns `app/` but not `/opt/venv` | `Dockerfile:32,41,43` | `docker exec tt-dev whoami` → `app`; `docker exec tt-dev id` → `uid=1000(app)` |
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
