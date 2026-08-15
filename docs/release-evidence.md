# Release Evidence

Factual record of the final-project release checks. Every result below was
produced by running the command shown, on this machine, on the `final-project`
branch. Items that were **not** verified are marked as such rather than assumed.

## Baseline

- **Branch:** `final-project` (branched from `ci-setup` at commit `582ee81`)
- **Date:** 2026-08-15
- **Python:** 3.10.11 local (`venv/`); CI and the Docker image both pin 3.11
- **Local app run command:**

  ```
  venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
  ```

  (verified on port 8002 to avoid a clash with an already-running instance)
- **`/health` result:** `HTTP 200` —
  `{"status":"ok","timestamp":"2026-08-15T19:26:16.478474+00:00"}`
  `GET /docs` also returned `HTTP 200`.
- **Frontend check:** Served with
  `python -m http.server 5500 --directory frontend` and opened at
  <http://localhost:5500> with the API running on port 8000. The Kanban board
  renders its three columns (To Do, In Progress, Done), a task can be created
  and appears on the board, and an existing task can be opened and edited.
  Verified in the browser by the author on 2026-08-15.
- **Test command:** `venv\Scripts\python.exe -m pytest -q`
- **Test result:** **125 passed, 3 warnings in 1.16s.** No failures.
  The three warnings are all the same benign one: Starlette deprecating
  `HTTP_422_UNPROCESSABLE_ENTITY` in favour of `HTTP_422_UNPROCESSABLE_CONTENT`,
  raised from `app/main.py:186`. The numeric status is unchanged. Pre-existing,
  not introduced by final work.

## CI evidence

- **Workflow file:** `.github/workflows/ci.yml` (a second workflow,
  `.github/workflows/docker-verify.yml`, builds and verifies the image)
- **Test command used by CI:** `pytest -v`, after
  `python -m pip install --upgrade pip` and `pip install -r requirements.txt`
- **Python version in CI:** `'3.11'`, quoted so YAML reads it as a string rather
  than the float `3.11`
- **Shortcut check — verified by reading the workflow files:**
  no `continue-on-error`, no `|| true`, no `--exit-zero`, pytest is not skipped
  and its output is not piped, and dependencies are installed from
  `requirements.txt`. A failing test therefore fails the check.
- **Latest run link:** ☐ **NOT VERIFIED — author to complete.** `gh` is not
  installed on this machine, so no workflow run has been observed from here.
  Paste the latest green run URL from the Actions tab of the repository.
- **Intentional red run (optional, from Module 4):** commit `75e5c8a` broke a
  health assertion deliberately and `48a6a95` reverted it. Both are pushed, so
  the two runs exist in the Actions history. Links not collected.

## Docker evidence

- **Build command:** `docker build -t task-tracker:final .` — completed
  successfully
- **Run command:** `docker run -d --name tt-final -p 8003:8000 task-tracker:final`
  (mapped to 8003 because 8000 was occupied by a local uvicorn)
- **`/health` check:** `HTTP 200` —
  `{"status":"ok","timestamp":"2026-08-15T19:27:26.960714+00:00"}`
  Also verified **from inside the container** earlier the same day, which rules
  out a host process answering on the mapped port.
- **Non-root check:** `docker exec tt-final whoami` → `app`;
  `docker exec tt-final id` → `uid=1000(app) gid=1000(app) groups=1000(app)`
- **No-baked-secrets check:** `.env`, `.git`, `tests`, `frontend`, `docs` and
  `requirements.txt` are all absent from `/app`. A positive control confirmed the
  image is not simply empty — `/app/app/main.py` and `/app/app/business_rules.py`
  are present.
- **Bytecode check:** 0 `__pycache__` or `.pyc` entries under `/app`
- **Image size:** 293MB per `docker images`; `docker image inspect .Size` reports
  68,732,880 bytes. The two disagree because the build produces an attestation
  manifest list; both are recorded rather than choosing one.
- **Runtime command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000` — no
  `--reload`, confirmed via `docker image inspect`.

### Note on when this became possible

For most of this project the Docker engine would not start — every API call
returned `500`, because WSL had no distributions installed. All Docker claims
were recorded as `[VERIFY]` pending evidence rather than asserted. After WSL was
installed the engine came up and the image was built for the first time, at which
point **one check failed** — see the first row of the log below.

## Documentation claim-vs-reality log

Six claims checked by executing something, not by re-reading the source.

| Claim checked | Evidence used | Result | Change made |
|---|---|---|---|
| `.dockerignore` excludes bytecode caches from the image | `docker build`, then `find /app -name '__pycache__' -o -name '*.pyc'` | **FALSE** — 10 `__pycache__` directories shipped. Bare patterns match only top-level entries; every cache is nested under `app/` | Fixed: `**/__pycache__` and `**/*.py[cod]`. Rebuild returns 0 entries. Commit `41b11f8` |
| `PATCH /tasks/{id}` fails only with 404 or 422 | `TestClient(app, raise_server_exceptions=False)` with `{"title": null}` | **FALSE** — returned **HTTP 500** | Fixed to 422 with 3 regression tests; 122 → 125. Commit `c616678` |
| Activity values over 80 chars are truncated | Created a task with 10 tags, read `/tasks/{id}/activity` | **FALSE for lists** — `to_value` was 218 chars, untruncated. True only for plain strings | Docstring corrected to match code; truncation logic deliberately unchanged |
| The API describes itself accurately at `/docs` | `GET /openapi.json` | **FALSE** — description read `"Module 1 learning project — REST API skeleton"` while the file defined 10 routes | Both the module docstring and the FastAPI `description` rewritten |
| README's Docker instructions are internally consistent | Read the two adjacent code blocks | **FALSE** — advised remapping to port 8001, then curled 8000, which would test the local server instead of the container | Warning added to the README |
| CI cannot silently pass a failing test | Read both workflow files for `continue-on-error`, `\|\| true`, `--exit-zero`, piped pytest | **TRUE** — none present | None needed |

### One claim that was checked and found true, and one that was wrong about itself

The `.dockerignore` row is the most useful entry here. A CI step named *"Assert
no bytecode caches shipped"* had been passing for weeks. It passes on a GitHub
runner because `actions/checkout` produces a fresh tree with **no `__pycache__`
at all** — so the assertion succeeds for want of anything to exclude, not because
exclusion works. Both `.dockerignore` assertions in `docker-verify.yml` are
non-discriminating in CI. The defect was only ever observable on a developer
machine that had run the test suite, and only after the engine could start.

## Items still to complete

- ☐ Frontend baseline sentence (Baseline section)
- ☐ Latest green Actions run link (CI section)
