# Final AI Review and Ownership Evidence

## AGENTS.md guardrails

`AGENTS.md` exists at the repository root, 164 lines.

- **Repo-specific stack and commands included:** **yes** — §2 carries a version
  table sourced to `requirements.txt`, `ci.yml` and the `Dockerfile`, plus the
  three commands (`uvicorn app.main:app --reload --port 8000`,
  `python -m http.server 5500 --directory frontend`, `pytest -v`). It also
  records that no `pyproject.toml`, `setup.py`, `pytest.ini` or `tox.ini` exists.
- **Docs-first / read-first guardrail included:** **yes** — §4 states "write to
  `docs/` by default", "inspect and report before proposing an edit", and "show
  the proposed content or diff and wait for approval".
- **Unexpected app/frontend edits rule included:** **yes** — §4 forbids changes
  to `app/` without explicit approval for one specific minimal fix, extending the
  same rule to `tests/`, `Dockerfile`, `.dockerignore` and `.github/workflows/`.

§3 additionally documents the business rules read out of the source: the
six-member status-transition allow-list, field limits, null-clearing semantics,
derived fields, and activity-log behaviour. §6 records known open items so a new
agent does not rediscover them and report them as new findings.

## AI code review mini-log

Reviewed diff: the `ci-setup` branch against `mid-course-project` — 941
insertions across `Dockerfile`, `.dockerignore`, two workflows, `CLAUDE.md`,
`README.md` and five files under `app/`. Ten comments were produced; the six most
significant are recorded here. Full log: `docs/module4/annotated-review-log.md`.

| AI comment | Grade | Reason | Verification or decision |
|---|---|---|---|
| `docker-verify.yml:108` "assert `.dockerignore` exclusions" step cannot fail | **Useful** | `Dockerfile:41` is the runtime stage's only source `COPY`; none of the asserted paths could reach `/app` even with `.dockerignore` deleted | Confirmed by reading the Dockerfile. Step renamed to what it proves. Later evidence made this sharper — see the manual check below |
| `app/main.py` module docstring and OpenAPI description claim "Module 1 skeleton, health only" | **Useful** | `GET /openapi.json` returned `description: Module 1 learning project — REST API skeleton` while the file defined ten routes | Verified by querying the running app. Both strings rewritten |
| `describe_value` docstring claims all values over 80 chars truncate | **Useful** | The `list`/`tuple` and `date` branches return before the length check | Measured: a 10-tag list stored 218 chars with no ellipsis. Docstring narrowed; logic deliberately left alone |
| `update_task` omits a 500 failure path | **Useful** | `TaskUpdate` types `title` as optional; `TaskResponse` types it non-optional, so the rebuild raises | Reproduced with `TestClient(raise_server_exceptions=False)` → **500**. Fixed to 422 with three regression tests |
| `ci.yml` double-runs on same-repo PRs | **Noise** | Real (`on: push` + `pull_request`, no branch filter) but costless on a learning project, and duplicate runs never produce a wrong result | No action |
| Top-level `docs/*.md` files "appear to be superseded stubs — verify before removing" | **Wrong** | Inferred staleness from line counts (11–23 vs 48–466) without reading `docs/README.md`, which states the duplication is deliberate because the brief names two locations | Rejected. Acting on it would have deleted a graded deliverable. See "One AI output I rejected" below |

## AI security mini-review

Read-only review of `app/`, `frontend/`, `tests/`, `Dockerfile`, `.dockerignore`
and both workflows. Seven findings were produced and graded. Full record:
`docs/security-review.md`.

| Finding | File evidence | Grade | Reason | Next action |
|---|---|---|---|---|
| No authentication or authorization on any route | `app/main.py:56-57` (CORS configured on that assumption, credentials disabled) | **Valid** | Intentional and documented course scope, but it is a limitation that would matter outside the learning context | Record as an accepted limitation. Do **not** add auth — forbidden by `AGENTS.md` §4 |
| `description` and `assignee` accept unbounded strings | `app/models.py:99, :102, :121, :124` — no length validator, versus `title` 200, comment `body` 2000, `author` 80, tags 24×10 | **Valid** | Only uncapped free-text fields, on a store that never evicts | Agree a cap; needs approval since it touches `app/` |
| `boardMessage` reaches `innerHTML` unescaped | `frontend/index.html:2037`, against the convention stated at `:1141-1143` and applied at ~20 sites | **Valid (Low)** | Breaks the file's own written rule | Defence-in-depth only — the data path was traced and **no exploitable input found** |
| `task_id` reflected verbatim into 404 detail | `app/main.py:150` and ten further sites | **Noise** | Served as JSON with no HTML context; echoing an id in a 404 is near-universal REST behaviour | None |
| CI actions pinned to tags rather than SHAs | `ci.yml:17, :20`, `docker-verify.yml:34` | **Noise** | Generic advice; neither workflow uses secrets and both set `permissions: contents: read` | None |
| `settings` imported but never used | `app/main.py:17` is the only non-`config.py` reference | **False Positive** (as security) | Dead code and non-functional config, not a vulnerability. Categorisation error — it appeared in a security table where it did not belong | Reclassified as maintainability |
| Dependency advisories for `python-dotenv` and `pytest` (from a second AI review) | `requirements.txt` pins 1.2.2 and 9.1.1 | **False Positive** | Both advisories are real, and both affect versions *below* the pins: CVE-2026-28684 affects `< 1.2.2`; CVE-2025-71176 affects `< 9.0.3`. The finding checked package names, not pinned versions | No upgrade warranted, which also removes the conflict with the rule against changing pins |

## Manual security check

**Finding M2 — a rejected drag shows the user the API's whole internal rule
table.** Found by operating the app, not by reading it.

I dragged a task from To Do straight to Done in the browser. The card snapped
back and a red banner appeared reading:

> Invalid status transition from ToDo to Done. Allowed transitions:
> `['Done->Done', 'Done->InProgress', 'InProgress->Done', 'InProgress->InProgress', 'ToDo->InProgress', 'ToDo->ToDo']`

That message is built in `app/business_rules.py:42`, which assembles the 422
detail by listing every pair in `VALID_TRANSITIONS` — so a rejected drag hands
the end user the API's complete internal rule table. It is not an XSS risk,
because the frontend inserts the detail with `textContent` rather than
`innerHTML`, but it is far more internal detail than a user needs, and the same
habit on a system with real business rules would leak valid values or schema
information through an error message. I would keep the 422 and the specific
reason, but shorten the message to name only the transitions available from the
task's current status, leaving the full table in the server logs.

**Why this counts as a human check.** The AI security review produced seven
findings and this was not among them. It raised a related one — task ids echoed
in 404 responses — and that was graded Noise. Neither review examined what a
rejected drag actually shows a user, because answering that requires operating
the application rather than reading it.

**The same failure mode, from the other direction.** The CI step asserting that
`.dockerignore` exclusions were applied had been green for weeks and could not
have failed: a fresh `actions/checkout` contains no `__pycache__` at all, so the
assertion passes for want of anything to exclude. The defect it was meant to
catch — ten bytecode directories shipping into the image — appeared the first
time the image was built on a machine that had actually run the test suite. Both
findings were invisible to code reading and both surfaced only when something was
run.

## One AI output I rejected or corrected

**Rejected: the claim that the top-level `docs/*.md` files were superseded stubs.**

An AI review compared line counts — 11–23 lines at the top level versus 48–466 in
`docs/midcourse/` — and concluded the shorter set was stale, recommending
verification before deleting either. The line-count evidence was accurate and the
conclusion was wrong. `docs/README.md` states the duplication is deliberate: the
course brief names two locations, so the full documents live in
`docs/midcourse/` and each is summarised at the top level.

Acting on that comment would have deleted a graded deliverable. It was the most
confident-sounding finding in the set and the only one supported purely by
inference about intent rather than by executing something. The claim was
retracted in `README.md` and in the technical note, and the reusable audit
checklist now opens with "read the index before judging the tree".

**Also corrected:** an AI-written plan asserted that the comment form's
`maxlength` attribute would need changing from 80 to 100. Opening
`frontend/index.html:1082-1092` showed there is **no** `maxlength` on either
input — one would have to be added. The correction is recorded in
`docs/decisions/comments-feature-plan.md`.

## Changes to app/ during final work

Per the brief's scope rule, one `app/` change is explained here.

**Change:** `app/models.py:128-144` — `TaskUpdate.validate_title` now rejects an
explicit `null`, and a new `validate_description` maps `null` to `""`.

**Why it qualifies as a small bug fix:** `PATCH {"title": null}` and
`{"description": null}` returned **HTTP 500** — a server error on ordinary user
input. `TaskUpdate` accepted both as optional while `TaskResponse` types them as
non-optional `str`, so rebuilding the task raised an unhandled `ValidationError`.

**Why the chosen behaviour:** it follows conventions already in the file rather
than inventing a stance. `title` is required, so `null` is a validation error,
mirroring how blank titles already returned 422. `description` clears to `""`,
mirroring create, where `app/storage.py:86` already normalises a null description
to `""`. `assignee`, `due_date` and `tags` already cleared cleanly at 200 and are
untouched — the fix makes the field set consistent rather than adding a new rule.

**Verification:** three regression tests added, including a sweep asserting no
nullable field can return 500. Suite went from 122 to 125 tests, all passing.
No product feature was added.

## Three AI usage rules

1. **Never paste:** credential and configuration files, and any command output
   containing personal identifiers. Evidence: `.env` was opened by a tool during
   an audit — its contents were harmless, which was luck of contents rather than
   of process; a personal email address entered a transcript via `git show`
   author fields; a copyrighted course slide showing an identifiable person was
   shared as an image. Recorded in `docs/governance-retrospective.md` §1.1.
2. **Always verify:** a claim about behaviour is not verified until it has been
   executed and the command recorded. Reading is not verification. Evidence: five
   documentation claims survived at least one careful read each and were false
   when executed, one of them producing an HTTP 500.
3. **Record AI contributions by:** a `Co-Authored-By` trailer on every commit
   containing AI-generated code, and a graded file in `docs/` for any AI review
   that informs a decision — written before the conversation ends, not after.
   Rejected output is recorded too, not only what was accepted.

## Ownership statement

I am comfortable submitting this repository as my own work because I verified it
rather than accepted it. I graded every AI security finding — seven in total —
and rejected four as Noise or False Positive, including one confident,
line-count-backed claim that would have deleted a graded deliverable had I acted
on it. The single change to `app/` is a bug fix I can explain: `PATCH` with an
explicit null title returned HTTP 500, it now returns 422, and three regression
tests cover it. Every result in `docs/release-evidence.md` came from a command I
can re-run, and the manual security finding above is one I found myself, by
dragging a task into an illegal column and reading what the API told the user.
I have not read all 2160 lines of `frontend/index.html`, and I would say so if
asked rather than claim more than I checked.
