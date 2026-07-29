# Prompt Log

The prompts that drove each feature, what the assistant returned, and what was
accepted, edited, or rejected. Abridged to the decisions — not full transcripts.

Tool: Claude (Claude Code) in the repo, with the ability to read files, run
`pytest`, and drive the running app in a browser.

---

## Orientation (before either feature)

### P0 — Read before writing

> Map this repo before changing anything. For `app/`: every model with exact
> field names and validators, every route, and how storage persists tasks. For
> `frontend/index.html`: how it calls the API, how cards render, how the modal
> submits. For `tests/`: fixtures and naming conventions, with two full test
> functions quoted so I can match the style. Do not propose changes yet.

**Returned:** an accurate map — `TaskCreate/TaskUpdate/TaskResponse` all
`extra="forbid"`, in-memory `dict[str, TaskResponse]`, `update_task` rebuilding
through `existing.model_dump()`, tests using a `client` fixture with autouse
storage reset.

**Accepted** in full, and it paid for itself immediately: that `model_dump()`
round-trip is exactly what a computed `is_overdue` field would have broken. The
"do not propose changes yet" clause mattered — earlier framing produced a
half-designed feature before the constraints were known.

---

## Feature 1 — Due dates + overdue filter

### P1 — Weak prompt, and the rewrite

**Weak (what not to send):**

> Add due dates to the task tracker.

**Why it is weak:** no type, no validation rules, no definition of "overdue", no
statement of where the rule lives, no test expectations, no scope limit. Every
one of those gets decided by the model silently, and the decisions surface later
as bugs.

**Rewritten:**

> Add an optional `due_date` to tasks in this FastAPI app. Constraints:
> - `due_date` is a calendar date (`datetime.date`), not a datetime. Optional,
>   defaults to null, accepted on both `POST` and `PATCH`.
> - Expose `is_overdue` on `TaskResponse` as a **computed** field, never stored —
>   it must become true when the date rolls over with no write to the task.
> - Overdue means the due date is **strictly** in the past **and** status is not
>   `Done`. Due today is not overdue. Judge against UTC, matching `created_at`.
> - Add a tri-state `overdue` query param to `GET /tasks` that ANDs with the
>   existing `status` / `priority` filters.
> - Touch `models.py`, `storage.py`, `main.py` only. No frontend yet. No new
>   dependencies. Show me the diff before applying it.

**Returned:** essentially the shipped backend.

**Edited:** the assistant put the overdue helper in `business_rules.py`, which
imports `TaskStatus` from `models.py` — so `models.py` importing back would be a
circular import. Moved the predicate into `models.py` next to the model that
derives from it, and left `business_rules.py` owning status transitions.

**Rejected:** an `overdue_only: bool = False` parameter. A plain boolean cannot
express "show me only the healthy tasks", and a default of `False` reads as
"not overdue" rather than "no filter". Kept `bool | None`.

### P2 — Pinning the semantics before the code

> Before writing the filter, list every boundary case for "overdue" and tell me
> what you would return for each: no due date; due today; due yesterday; due
> yesterday but status Done; due tomorrow. If any of those is a judgement call
> rather than an obvious answer, say so instead of picking.

**Returned:** the table, with **due today** and **Done + past due** flagged as
judgement calls — the right two.

**Accepted** as the specification, then contradicted the assistant on both:
its first implementation used `<=` (due today is overdue) and had no status
check (finished-late stays red). Asking for the boundaries *before* the code is
what made the disagreement visible while it was still cheap.

### P3 — Tests that would fail if the rule were wrong

> Write pytest tests for due dates matching the existing file's style: `client`
> fixture, no imports beyond stdlib, one behaviour per test, names of the form
> `test_<action>_<condition>_<expected>`. Cover the boundaries specifically —
> due today must not be overdue, and a `Done` task with a past date must not be
> overdue. Compute dates relative to today; do not hardcode 2026.

**Returned:** 17 tests, all passing.

**Edited:** dates were initially hardcoded (`"2026-07-26"`), which would have
made the suite start failing on a future date. Replaced with a
`_days_from_today()` helper computed in UTC to match the server.

**Accepted:** the extra cases it volunteered — `2026-02-30` (well-formed but
impossible) and `?overdue=maybe` (a query param that must 422).

### P4 — Frontend, with the rule left on the server

> Wire due dates into `frontend/index.html`: a date input in the modal (empty =
> null), a due/overdue pill on cards, and an "Overdue only" toggle in a filter
> bar above the board. The toggle must call `GET /tasks?overdue=true` — do not
> reimplement the overdue rule in JavaScript. Keep all three columns visible when
> filtering. Match the existing CSS variables and card markup.

**Returned:** the toolbar, pill and toggle, close to as-shipped.

**Rejected:** a `formatDueDate` built on `new Date(task.due_date)`. That parses a
bare `YYYY-MM-DD` as UTC midnight and renders the previous day for anyone west of
Greenwich. Replaced with an explicit split into a local `Date`.

**Accepted with an addition:** the card template interpolated `task.title`
straight into `innerHTML`. Pre-existing, but tags were about to add more
user-controlled text to the same template, so an `escapeHtml` pass went in.

---

## Feature 2 — Tags / labels

### P5 — Scope control, up front

> I want tags on tasks. Before proposing an implementation, give me two options:
> the smallest thing that supports chips on cards and filter-by-tag, and the
> "proper" normalised version. For each, list the files touched and the new
> endpoints. Do not write code yet.

**Returned:** (a) a validated `list[str]` on the task, no new endpoints;
(b) `Tag` + `TaskTag` models, `/tags` CRUD, rename-with-cascade, usage counts.

**Rejected (b)** outright and recorded it in the ADR. The store is a dictionary
in memory — there is nothing to normalise into, and it would have been a bigger
feature than the two it was meant to sit beside. Asking for the options
*before* code meant rejecting it cost one message instead of a revert.

### P6 — Validation rules stated, not inferred

> Implement tags as `list[str]` on `TaskCreate` / `TaskResponse`, defaulting to
> `[]`. Validation: trim each tag; reject blank after trimming; max 24 chars per
> tag; max 10 tags per task; drop duplicates **case-insensitively but preserve
> the casing the user typed** — `["Bug","bug","ui"]` becomes `["Bug","ui"]`.
> On `TaskUpdate`, an explicit `"tags": null` clears them; an omitted key leaves
> them untouched. Follow the `_validate_title` pattern already in the file.

**Returned:** `_validate_tags` matching the existing helper style.

**Edited:** the first version normalised with `.lower()`, so a user typing `API`
got `api` back. The dedup key is now `casefold()` while the stored value keeps
the original spelling — dedup without rewriting user input.

**Accepted:** raising on too many tags *before* the per-tag loop, so 200 junk
tags produce one clear error rather than a 200-item scan.

### P7 — The filter, and a design bug caught by asking

> Add a case-insensitive `tag` query param to `GET /tasks` that ANDs with the
> existing filters. Then, for the frontend tag dropdown: where does the list of
> selectable tags come from, given the board request is itself filtered?

**Returned:** the backend filter, plus — because the second half was asked as a
question — the recognition that building the dropdown from the filtered response
collapses it to the selected tag, with no way back to "All tags".

**Accepted** the fix: a separate unfiltered request for the vocabulary whenever a
filter is active. Two requests instead of one, in exchange for a filter you can
undo. Framing it as a question rather than an instruction is what surfaced it —
an instruction would have produced the collapsing version and a bug report later.

### P8 — Adversarial pass on my own tests

> Take the tag tests and try to break the implementation without failing any of
> them. If you find a rule a test claims to cover but does not actually pin,
> name it.

**Returned:** the observation that dedup was asserted only through the response
body, so a change to the *filter's* case handling would slip through untested.

**Accepted:** added `test_list_filter_by_tag_is_case_insensitive`, which is
exactly the test Break 4 later proved effective.

---

## Refactor and verification

### P9 — Refactor with the contract stated first

> `handleTaskSubmit` now has seven near-identical compare-and-set blocks mirrored
> by seven assignments in the create branch. Before changing anything, write down
> the behaviour contract as a list of observable outcomes. Then refactor both
> branches onto one field-descriptor list. The contract must hold exactly — I
> will verify by intercepting `window.fetch`.

**Returned:** a five-point contract, then the descriptor-list version.

**Accepted**, with one flag worth recording: the old code used `||` for the
"field absent" fallback, the new code uses `??`. They agree for every current
field, but they diverge the moment a falsy value is legitimate. Noted in the
commit message rather than left for someone to find.

### P10 — Break Tests

> For each of these four rules, break it in the source, run only the test that
> should catch it, and show me the failure output — then restore the file and
> re-run the full suite. Rules: the overdue `<` boundary; the `Done` exemption;
> case-insensitive tag dedup; case-insensitive tag filtering.

**Returned:** a script that patched, ran, and restored each file.

**Edited:** the first version left `models.py` **broken** when a subprocess call
failed partway — no `try/finally`. Rewritten to restore in a `finally` block and
assert the file is clean before starting. Worth logging: a tool that edits source
in place needs its rollback to be the part you check hardest.

---

## Feature 3 — Search + combined filters

### P11 — Shape the API before writing it

> I want text search on tasks. Before any code: should this be a new
> `/tasks/search` endpoint or another query parameter on `GET /tasks`? Argue
> both, then say which you would ship given that `status`, `priority`, `overdue`
> and `tag` already exist and already AND together.

**Returned:** both options, and the right recommendation — a `q` parameter,
because a separate endpoint has to re-declare the four existing filters or
refuse to combine with them.

**Accepted.** Worth noting the assistant's *unprompted* first instinct in an
earlier draft had been the separate endpoint; asked to argue both sides it
talked itself out of it. Asking for the comparison cost one message.

### P12 — Pin the matching rules, including the boring ones

> Implement `q` on `GET /tasks`. Rules: case-insensitive; substring, not prefix;
> matched against title **or** description and nothing else; the term is literal,
> so `?q=.*` finds tasks containing the characters `.*`; trimmed, and blank after
> trimming means no filter rather than no matches. ANDs with the existing four.
> Touch `storage.py` and `main.py` only.

**Returned:** the shipped implementation.

**Rejected:** an earlier suggestion to search `assignee` and `tags` as well.
Typing `backend` would then return tasks that merely carry a `backend` tag,
duplicating the dropdown next to the search box and making results impossible to
explain. Free-text search over free-text fields.

**Rejected:** splitting the query on whitespace and ORing the words. `pay api`
matching everything containing `api` reads as a bug to anyone who meant the
phrase.

### P13 — Make it not hammer the server

> Wire the search box into the toolbar. It must not issue a request per
> keystroke. Then tell me how you would *prove* the debounce works rather than
> assert it does.

**Returned:** a 250ms debounce, plus the suggestion to wrap `window.fetch` and
count calls while dispatching synthetic `input` events.

**Accepted**, and it paid off: typing an eight-letter word produced exactly one
board request instead of eight (16 including the tag-vocabulary fetch). That
measurement is in [verification.md](verification.md), not a claim in a comment.

---

## Feature 4 — Comments + activity log

### P14 — Scope first, again

> I want comments and an activity log on tasks. Before proposing anything, list
> what you would *not* build and why, given this is an in-memory store with no
> users and no auth. Then give me the smallest version that still shows a
> timeline and a comment thread in the UI.

**Returned:** a sensible exclusion list — threading, @mentions, edit history,
a board-wide feed — and a two-model design with nested routes.

**Accepted**, with one addition: comments are **append-only**. Deleting a comment
immediately raises "does its `commented` activity entry go too?", and either
answer makes the log lie. That question is bigger than the feature; not having it
is cheaper than answering it.

### P15 — The design decision that mattered

> For the activity log: if a single PATCH changes both priority and due date, do
> you write one entry or two? Give me the rendering consequences of each, not
> just the storage consequences.

**Returned:** initially one entry per request holding a dict of changed fields.
Pushed on rendering, it conceded that the timeline then displays JSON blobs and
that "when did the priority last change?" requires opening every entry.

**Edited to per-field entries.** The log now reads as sentences —
`Priority: Medium → High`. Break 8 exists to stop this regressing.

**Accepted:** its point that `updated_at` must be excluded from the tracked
fields, or every change would log twice.

### P16 — Where the recording lives, and what it must not touch

> Record activity in `storage.py`, not the routes — it is the only layer that
> sees the task before and after. Constraints: a PATCH re-sending a field's
> current value logs nothing; posting a comment records an entry but must **not**
> change the task's `updated_at`, because commenting is not editing; deleting a
> task removes its comments and activity.

**Returned:** the shipped storage layer.

**Rejected:** keeping activity rows after the task was deleted, argued as
"audit logs should be append-only". Activity is only reachable through
`GET /tasks/{id}/activity`, which 404s once the task is gone — so the rows were
unreadable by construction and simply leaked. A durable audit log is a different
feature with a different endpoint.

### P17 — Adversarial pass, and a test that could not fail

> Here are the new comment and activity tests. Find any that would still pass if
> I broke the rule they claim to cover.

**Returned:** the observation that
`test_commenting_does_not_change_the_task_updated_at` asserts the timestamp is
*unchanged* — which is true automatically, because the system clock does not
advance during a sub-millisecond request. It would pass even if commenting did
stamp the task.

**Accepted**, and it generalised: the same clock granularity made a *pre-existing*
test (`test_patch_partial_update_keeps_other_fields`) flaky in the opposite
direction. Measuring rather than retrying showed 20,000 calls to `datetime.now()`
returning two distinct values. Both tests now wait out a clock tick. Full write-up
in [verification.md](verification.md) §6.

### P18 — Refactor, contract stated first

> There are now two modals duplicating the same shell: toggle `is-open`, mirror
> `aria-hidden`, lock body scroll, close on ×/backdrop/Escape — including two
> separate document keydown listeners. Write the observable behaviour contract
> first, then collapse both onto one controller. I will verify by wrapping
> `window.fetch` and reading the DOM.

**Returned:** a twelve-point contract and the `createModal` helper.

**Accepted**, with one correction: the first version ran the caller's `onOpen`
*after* revealing the dialog, which flashes the previous task's values for a
frame, and tried to focus the title input before it was visible — focus silently
fails on a hidden element. Populate before showing; focus after.
