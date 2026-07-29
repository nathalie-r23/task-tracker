# Mini-ADR — Due Dates and Tags

**Status:** accepted · **Branch:** `mid-course-project` · **Baseline:** 24 tests passing at `18a2672`

Decision note written before implementation and updated with what actually
shipped. It records the choices that had real alternatives, and the suggestions
that were turned down as too big for the module.

---

## Context

The Task Tracker is a FastAPI backend with an in-memory store and a single-file
Kanban frontend. Tasks already had title, description, status, priority and
assignee, plus a status-transition rule. Two features were added end to end.

---

## Decision 1 — `is_overdue` is computed on read, not stored

`TaskResponse` exposes `is_overdue` as a Pydantic `@computed_field` derived from
`due_date` and `status`.

**Alternative rejected — a stored boolean column.** It is wrong the moment the
clock passes midnight. Nothing writes to a task at midnight, so a stored flag
would need a scheduled sweep to stay true. A derived value is correct by
construction.

**Alternative rejected — computing it only in the browser.** The board would
have been right, but `GET /tasks?overdue=true` could not exist, and the rule
would have lived in untested JavaScript. Computing server-side means the API
filter and the UI badge share one implementation, covered by pytest.

**Consequence worth recording.** `storage.update_task` rebuilt a task with
`TaskResponse(**existing.model_dump())`. `model_dump()` emits computed fields,
and `TaskResponse` is declared `extra="forbid"` — so adding the computed field
would have made *every* `PATCH` fail. It now rebuilds from
`TaskResponse.model_fields`, which by definition excludes computed fields. This
was found by reading the storage layer before writing the model, not by
debugging a broken suite.

## Decision 2 — Overdue means late *and* still open

`due_date < today_utc() and status != Done`.

- **Strictly `<`.** A task due today is not overdue; the day is not over.
- **`Done` is exempt.** "Overdue" drives attention. Finished work needs none,
  even if it landed late. If "finished late" reporting is ever wanted, that is a
  different field and a different question.
- **UTC.** `created_at` / `updated_at` are already UTC. Judging dates by the
  server's local date would make behaviour depend on where the process runs.

Both boundaries are pinned by Break Tests rather than left to a comment.

## Decision 3 — Filters run on the server, and compose

`GET /tasks` takes `status`, `priority`, `overdue` and `tag`, all optional, all
ANDed. `overdue` is deliberately tri-state — absent / `true` / `false` — so
"only overdue" and "only healthy" are both expressible.

The frontend sends query parameters instead of filtering the array it already
holds, so there is exactly one implementation of each rule.

## Decision 4 — Tags are a validated list of strings

Trimmed; blanks rejected; max 24 characters each; max 10 per task; duplicates
dropped case-insensitively, keeping the first spelling entered.

**Alternative rejected — a normalised tag table with its own IDs and endpoints.**
The assistant proposed `Tag` and `TaskTag` models, `/tags` CRUD, rename-cascades
and usage counts. That is a feature in its own right, and the store is a
dictionary in memory — there is no database to normalise into. Out of scope.

**Alternative rejected — lower-casing tags on write.** Canonical, but it hands
back something the user did not type. Case-insensitive comparison with
case-preserving storage gets the dedup and the filtering without the surprise.

## Decision 5 — Explicit `null` clears, omission preserves

`PATCH` already used `exclude_unset=True`, so "field absent" and "field set to
null" are distinguishable. `{"tags": null}` and `{"due_date": null}` clear the
value; omitting the key leaves it alone. Tags are stored as `[]`, never `null`,
so the response shape is stable.

## Decision 6 — The tag dropdown needs its own unfiltered request

The board request is filtered, so it cannot also populate the tag vocabulary —
filtering by `backend` would leave `backend` as the only selectable tag. When a
filter is active the frontend issues a second, unfiltered request purely for the
tag list. Two requests where one would do, in exchange for a filter you can back
out of.

---

## Changes made in passing

- **Card fields are HTML-escaped.** `renderTaskCard` interpolated `task.title`
  straight into `innerHTML`. Adding user-controlled tags to the same template
  made that worth fixing rather than widening; all card text now goes through
  `escapeHtml`.
- **Due dates are parsed field-by-field, not via `new Date(str)`.** Passing a
  bare `YYYY-MM-DD` to `Date` parses it as UTC midnight, which renders as the
  *previous day* for any user west of Greenwich.
- **CORS accepts any localhost origin by regex** instead of three hardcoded
  ports, so the board works whatever port the static frontend is served on.

## Explicitly out of scope

Recurring due dates · reminders and notifications · tag rename/merge · tag
colours · per-user "my overdue tasks" · saved filter presets · bulk re-tagging ·
timezone-aware per-user overdue calculation.
