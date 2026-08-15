# Module 5 Security Review

Read-only security review of the Task Tracker repository, plus grading and
reconciliation of the findings it produced.

**Repository state at review time:** commit `e4bdb61` on branch `ci-setup`, plus
untracked `AGENTS.md`.
**Method:** static inspection only. No tests were run, no application started, no
container built. Findings marked otherwise are inference, not measurement.
**Reviewer:** Claude Code (AI), read-only. Manual scan section is **not yet
completed** — see §3.

---

## 1. AI findings, graded

Grades use the Module 5 definitions:

- **Valid** — a real issue in this repo, or a course-scope limitation that would
  matter outside the learning context.
- **False Positive** — wrong because of the actual code, severity, behaviour, or
  Task Tracker scope.
- **Noise** — technically true but too generic, trivial, or unsupported to
  become an action item.

| ID | Finding | Severity as reported | Grade | File evidence |
|---|---|---|---|---|
| S0 | No authentication or authorization on any route | *not reported as a finding* | **Valid** | `app/main.py:56-57` (CORS configured on that assumption, `allow_credentials=False`); documented as intentional in `AGENTS.md` §1, `README.md` limitations, `CLAUDE.md` §7 |
| S1 | `description` and `assignee` accept unbounded strings | Medium | **Valid** | `app/models.py:99, :102, :121, :124` — no length validator. Contrast `title` max 200 (`:24`), comment `body` max 2000 (`:197`), `author` max 80 (`:211`), tags 24 chars × 10 (`:39-49`) |
| S2 | `boardMessage` interpolated into `innerHTML` without escaping | Low | **Valid (Low)** | `frontend/index.html:2037`; escaping convention stated at `:1141-1143` and applied at ~20 other sites; source traced `:1320` ← `:1305` ← server `detail` |
| S3 | `task_id` reflected verbatim into error detail | Low | **Noise** | `app/main.py:150, :185, :190, :206, :215, :237, :246, :261, :270, :288, :297`. Served as JSON, no HTML context; echoing an id in a 404 is near-universal REST behaviour |
| S4 | CI actions pinned to mutable tags rather than SHAs | Low | **Noise** | `.github/workflows/ci.yml:17, :20`; `.github/workflows/docker-verify.yml:34`. Generic advice; neither workflow uses secrets and both set `permissions: contents: read` |
| S5 | `settings` imported but never used | Low | **False Positive** (as security) | `app/main.py:17` is the only non-`config.py` reference. Dead code and non-functional config, not a vulnerability. Valid as a maintainability observation |
| S6 | `tests/verify_a.py` is not a pytest module | Info | **False Positive** (as security) | Defines `expect_fail`/`expect_ok` and prints; no `test_` functions, so `pytest --collect-only` counts none of it. Governance, not security |

**Tally:** 3 Valid · 2 Noise · 2 False Positive.

### Note on S0

S0 was **omitted** from the original findings table, filed under "no issue found
— intentionally absent." That was an under-report. The absence of auth is
simultaneously a deliberate course-scope decision *and* a limitation that would
matter outside the learning context, which meets the definition of Valid. The
omission is recorded here because how a reviewer classifies an intentional gap
is itself a finding about the review.

---

## 2. Categories inspected with no issue found

- **Secrets and config.** `.env` is gitignored (`.gitignore:14`), confirmed not
  tracked, excluded from the image by `.dockerignore:8`, and holds only `PORT`
  and `APP_ENV`. Values were never printed during the review.
- **Error handling.** `grep -rnE "except|traceback|debug=True|print\("` over
  `app/` returns zero matches. No bare except, no swallowed exception, no debug
  flag.
- **Enum handling.** `TaskStatus` and `TaskPriority` are three-member string
  enums; FastAPI rejects anything else with 422 before handler code runs.
  Transitions are a closed six-member allow-list (`app/business_rules.py:5-12`)
  — fails closed.
- **Filter-summary rendering.** Raw search input at `frontend/index.html:2069`
  sinks to `summary.textContent` (`:2101`), not `innerHTML`. Not exploitable.
- **Docker.** Non-root `app` uid 1000, `USER` before `CMD`, `python:3.11-slim`
  pinned in both stages, no `ADD`, no secret-bearing `ENV`/`ARG`, only `app/`
  copied into the runtime stage.
- **Dependencies.** All seven pins in `requirements.txt` are exact `==`. No
  vulnerability scanning runs in CI — noted, not filed as a finding.

---

## 3. Manual scan findings

Recorded from the reviewer's own manual pass.

| ID | Finding | File evidence | Grade |
|---|---|---|---|
| M1 | Task ids echoed back in 404 responses | `app/main.py:150` and ten further `HTTPException` sites | **Overlaps AI S3** — see §4 |
| M1 | Task ids echoed back in 404 responses | `app/main.py:150` and ten further `HTTPException` sites | **Overlaps AI S3** — see §4 |
| M2 | Verbose validation text shown in the frontend | `frontend/index.html:1305`, :1499, :1510, :1844; source `app/business_rules.py:42` | **Confirmed, Low** |
| M3 | Network boundaries for the Docker deployment are undocumented | `Dockerfile:45`, :49; `app/main.py:56-57` | **Confirmed as a documentation gap, Low** |

### M2 — evidence located

The frontend takes the server's `detail` string verbatim
(`frontend/index.html:1305`) and renders it through `showFieldError` (:1499),
`showFormError` (:1510) and `showCommentError` (:1844).

All three use `textContent`, so there is **no XSS here** — this is purely about
verbosity. The most verbose source is `app/business_rules.py:42`, whose 422
detail enumerates *every* allowed status transition. A user who drags a card
from ToDo to Done sees the complete internal transition allow-list in a banner.

Harmless in this application — the rules are public and documented in
`README.md`. It is listed because the *pattern* of piping server error strings
straight to the UI leaks internal structure on systems where the rules are not
public.

### M3 — evidence located

The gap is real but is documentation, not configuration. `Dockerfile:45` exposes
port 8000 and `:49` binds uvicorn to `0.0.0.0`, which is correct inside a
container but is nowhere stated as deliberate. `app/main.py:56-57` restricts CORS
to localhost origins plus `"null"`, which assumes the browser and the API share a
host — an assumption that silently breaks the moment the container is reached
from anywhere other than the Docker host.

Nothing is deployed, so there is no live boundary to audit. Recording the
assumption is the action, not changing it.

---

## 4. Reconciliation

**Status: incomplete.** Agreement and You-only both depend on §3.

| Agreement | AI-only | You-only |
|---|---|---|
| **S3 / M1** — task ids echoed in 404 responses. Both reviews found it; the AI graded it Noise, the manual pass kept it as a lower-severity note | **S0** no auth · **S1** unbounded `description`/`assignee` · **S2** unescaped `innerHTML` · **S4** CI tag pins · **S5** unused `settings` import · **S6** `verify_a.py` not a pytest module | **M2** verbose validation text in the frontend · **M3** undocumented network boundaries for Docker |

### Reconciliation note

M1 was initially recorded as You-only. It is in fact **Agreement**: the AI
review filed the same issue as S3 (`app/main.py:150` and ten further sites) and
graded it **Noise**. Both reviews saw it; they disagreed on whether it was worth
acting on. That disagreement is more informative than either verdict alone —
the AI dismissed it as generic REST behaviour, the manual pass kept it as a
usability and information-disclosure note.

### A second AI review, not reconciled here

A separate AI review (different tool) reported **OSV-backed dependency
advisories for `python-dotenv` and `pytest`**, plus CI/Docker supply-chain
hardening around tag pins, image pins and unhashed installs.

**RESOLVED — 2026-08-15.** An advisory lookup was run. Both advisories are real,
and **this repository is already on the patched version of each**:

| Package | Pinned | Advisory | Affected range | This repo |
|---|---|---|---|---|
| `python-dotenv` | **1.2.2** | CVE-2026-28684 / GHSA-mf9w-mj56-hr94 — symlink following in `set_key` allows arbitrary file overwrite via cross-device rename fallback (Medium) | **< 1.2.2** | **Not affected.** 1.2.2 *is* the fix |
| `pytest` | **9.1.1** | CVE-2025-71176 / GHSA-6w46-j5rx-g56g — predictable `/tmp/pytest-of-{user}` directory permits local DoS or privilege gain on UNIX | **< 9.0.3** | **Not affected.** Also a dev-only test runner, not shipped in the image |

**Verdict: the second review's dependency findings are False Positives for this
repository.** The advisories exist at the *package* level; the finding did not
check them against the *pinned versions*. The reviewer's own note — that the
advisories were not independently reproduced beyond checking pinned versions —
turns out to be the decisive gap.

This also settles the contradiction with §2, which listed dependencies as clean.
Both statements were defensible on the evidence each had; the lookup shows §2 was
correct, though for a weaker reason than stated — exact pinning is not itself
protection, and the pins happened to be current.

**No upgrade is warranted.** `AGENTS.md` §4 and `CLAUDE.md` forbid changing pins
without approval, and there is now nothing to fix. Note that `pytest` does not
reach the runtime image at all: the Dockerfile copies only `app/`, so a test-only
dependency could not affect a running container regardless.

Sources: [python-dotenv advisory](https://github.com/advisories/GHSA-mf9w-mj56-hr94) ·
[pytest advisory](https://github.com/advisories/ghsa-6w46-j5rx-g56g) ·
[CVE-2025-71176 detail](https://www.cvedetails.com/cve/CVE-2025-71176/)

### Observation on the shape of AI coverage

AI coverage clustered where a data path could be traced mechanically — a missing
validator, an unescaped sink, a dead import — and thinned out wherever judgement
about *scope* was required, which is why it filed "no authentication" under clean
rather than as a scope-limited risk.

Its weakest three findings came from pattern-matching generic checklists (CI
pinning, reflected identifiers, tidiness in `tests/`), so the failure mode to
watch is not hallucination but confident padding: real observations promoted
into a security table where they do not belong.

---

## 5. Top-3 backlog

Drawn from the three Valid findings — this is the complete set, not a selection.

| Rank | Finding | Why it matters | Owner | Next action |
|---|---|---|---|---|
| 1 | **S0** — no authentication or authorization | Every route is unauthenticated CRUD. Intentional and documented, but the largest gap between this repo and anything deployable; it shapes CORS, rate limiting and data exposure downstream | **Course/project owner** | Record as an accepted, documented limitation with the conditions that would change it. Do **not** add auth — `AGENTS.md` §4 and `CLAUDE.md` §7 forbid it without approval |
| 2 | **S1** — unbounded `description` / `assignee` | The only uncapped free-text fields, on a store that never evicts. Inconsistent with every sibling field | **Backend** | Agree a cap (2000, matching comment bodies, is the natural precedent), then a bounded change to `app/models.py` plus tests. Requires explicit approval — Module 5 guardrails put `app/` off-limits |
| 3 | **S2** — unescaped `innerHTML` | Breaks the file's own convention, stated in a comment 900 lines above the violation. The one place server text reaches the DOM raw | **Frontend** | Wrap `boardMessage` in the existing `escapeHtml()` at `frontend/index.html:2037`. One line, no behaviour change. See §6 |

Excluded deliberately: S3 and S4 (Noise), S5 and S6 (False Positive as
security). S5's underlying fact — `PORT` in `.env` has no effect — is real and
belongs on a maintainability list.

### Comparison with the second review's backlog

The other AI review produced a top-3 that agrees on the first two items and
differs on the third:

| Rank | This review | Second review | Agreement? |
|---|---|---|---|
| 1 | S0 — no auth | "Add authentication, authorization, and task ownership before any real deployment" (Medium if deployed, Backend) | **Yes.** The second review adds *task ownership*, which this review did not raise — with no users there is no owner concept, so it is a real extension |
| 2 | S1 — unbounded `description`/`assignee` | "Bound request and storage growth for task fields and total task count" (Medium, Backend) | **Yes**, and broader: it also bounds *total task count*, which this review missed entirely. The store has no cap on the number of tasks, only on some field lengths |
| 3 | S2 — unescaped `innerHTML` | "Upgrade vulnerable/dev-risk dependencies and tighten supply-chain pins" (Medium, Platform) | **No — resolved against the second review.** The advisory lookup in §4 shows both pinned versions are already patched, so there is nothing to upgrade. S2 stands as rank 3 |

Two items from the second review are genuine gaps in this one: **task ownership**
as a concept, and a cap on **total task count** rather than only field lengths.
Both are recorded here rather than silently merged into §5, because neither has
been independently verified in this repository.

---

## 6. Proposed one-line fix (S2) — NOT APPLIED

```diff
--- a/frontend/index.html
+++ b/frontend/index.html
@@ -2034,7 +2034,7 @@
             return;
         }

-        const boardMarkup = `${boardMessage ? `<div class="board-message error">${boardMessage}</div>` : ""}${renderBoard()}`;
+        const boardMarkup = `${boardMessage ? `<div class="board-message error">${escapeHtml(boardMessage)}</div>` : ""}${renderBoard()}`;
         board.innerHTML = boardMarkup;
         attachBoardInteractions();
```

**Why it is small enough for Module 5:** one line, one file, no new code
(`escapeHtml` is defined at `:1143` and used at ~20 sites), no new dependency, no
refactor, and no behaviour change for correct input — `escapeHtml` rewrites only
`& < > " '`, none of which appear in any `detail` string the server can currently
produce.

**Honest scoping note:** this is defence-in-depth. The data path was traced and
**no exploitable input was found** — every reachable `detail` is server-generated
text plus a UUID. If the rubric requires demonstrated exploitability, the correct
decision is backlog rather than fix.

**Verification (manual — this file has no test coverage):** start the API and
frontend, drag a task from ToDo directly to Done to trigger the 422 rejection
(`app/business_rules.py:38-43`), and confirm the red banner text is **identical
before and after** the change. Visible `&gt;` or `&#39;` would indicate
over-escaping.

---

## 7. Limits of this review

- `frontend/index.html` was read **selectively** — roughly 400 of 2160 lines,
  targeted at escaping, error handling and rendering sinks. S2 is a confirmed
  gap; the file is not certified free of other unescaped sinks.
- **Nothing was executed.** S1's memory-growth reasoning follows from the absence
  of a validator plus a never-evicting store; it was not measured.
- **Rate limiting, request size caps and DoS hardening** are absent and were not
  filed as findings. For a single-process, no-auth, in-memory course project
  their absence is a scope decision rather than a defect.
- **No `app/` changes were made during this review.** The repository's last
  behavioural change was Module 4 commit `c616678`, which made
  `PATCH {"title": null}` answer 422 instead of 500.

## Files inspected

`AGENTS.md` · `README.md` · `CLAUDE.md` · `app/main.py` · `app/models.py` ·
`app/storage.py` · `app/business_rules.py` · `app/core/config.py` ·
`app/schemas/health.py` · `app/api/routes/health.py` · `requirements.txt` ·
`.env.example` · `.env` (key names only, values redacted) · `.gitignore` ·
`Dockerfile` · `.dockerignore` · `.github/workflows/ci.yml` ·
`.github/workflows/docker-verify.yml` · `frontend/index.html` (lines ~1100-1160,
1290-1330, 1640-1800, 2030-2115) · `tests/` listing and `tests/verify_a.py` head.

Confirmed absent: `pyproject.toml`, `setup.py`, `setup.cfg`, `pytest.ini`,
`tox.ini`, any compose file.
