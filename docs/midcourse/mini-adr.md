# Mini-ADR — Due Dates, Tags, Search, Comments

**Status:** accepted · **Branch:** `mid-course-project` · **Baseline:** 24 tests passing at `18a2672`

Decision note written before implementation and updated with what actually
shipped. It records the choices that had real alternatives, and the suggestions
that were turned down as too big for the module.

Decisions 1–6 cover the two features the brief asks for (due dates, tags).
Decisions 7–13 cover the two built afterwards (search, comments + activity) and
were written before that code existed, same as the first six. Decision 14
reverses part of Decision 12 and explains why the earlier reasoning stopped
holding.

---

## Context

The Task Tracker is a FastAPI backend with an in-memory store and a single-file
Kanban frontend. Tasks already had title, description, status, priority and
assignee, plus a status-transition rule. Four features were added end to end.

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

## Decision 7 — Search is a query parameter, not an endpoint

`GET /tasks?q=...` rather than `GET /tasks/search?q=...`.

**Alternative rejected — a dedicated search endpoint.** It would have had to
re-declare `status`, `priority`, `overdue` and `tag` to stay useful, leaving two
routes with the same filter logic to keep in step — or it would have refused to
combine, making "overdue backend tasks mentioning migration" unexpressible. `q`
joins the existing AND chain and costs one parameter.

**Alternative rejected — filtering the fetched array in the browser.** Same
argument as Decision 3. The board would be right and the API would not.

## Decision 8 — Search covers title and description, and nothing else

Case-insensitive substring against `title` **or** `description`.

**Alternative rejected — searching assignee and tags too.** The assistant's
default. It makes results unexplainable: typing `backend` returns tasks that
merely carry a `backend` tag, silently duplicating the dropdown next to the
search box. Free-text search over free-text fields; structured fields get
structured filters.

**Alternative rejected — tokenising the query and ORing the words.** `pay api`
would then match everything containing `api`, which reads as a bug to anyone who
meant the phrase. The term is matched literally, including punctuation, so `.*`
searches for the characters `.*` and not a regex.

**Boundary pinned:** `q` is stripped, and empty-after-stripping means *no
filter*. Otherwise `?q=%20` would match nothing and look broken.

## Decision 9 — Activity is stored; it cannot be derived

`is_overdue` is computed on read because current state is enough to know it.
History is not recoverable from current state, so activity entries are written at
the moment of the change and kept.

## Decision 10 — One activity entry per changed field

A `PATCH` that changes priority and due date writes two entries, each naming the
field, the old value and the new one.

**Alternative rejected — one entry per request holding a dict of changes.** The
assistant's first version. The timeline then renders as JSON blobs, and "when did
the priority last change?" requires the reader — or a query — to open every
entry. Per-field entries render as sentences and are filterable by field for
free. The cost is more rows, which for an in-memory learning project is nothing.

## Decision 11 — Activity is recorded in the storage layer

`storage.update_task` is the only place that sees the task before and after the
change. Recording in the route would mean re-reading the task first and keeping
the diff logic in step with storage.

**Consequence:** values are heterogeneous — dates, enums, lists, long strings —
so they are stringified for the log (`_describe`), enums by `.value`, dates by
`.isoformat()`, tag lists comma-joined, empty as `null`. Values are truncated at
80 characters so pasting an essay into a description does not put a copy of it in
the log twice.

## Decision 12 — Comments are append-only

`POST` and `GET`. No edit, no delete.

**Alternative rejected — full comment CRUD.** Deleting a comment immediately
raises "does the `commented` activity entry go too?", and if it does the log
lies, and if it does not the log points at nothing. That is a real design
question and a bigger one than the feature warrants here. Append-only has no such
question, and the limitation is honest rather than hidden.

## Decision 13 — `comment_count` is derived at read, but is a plain field

Every storage read stamps `comment_count` from the comment store before returning
a task, so it cannot drift from the actual number of comments.

**Why not a `@computed_field` like `is_overdue`?** `is_overdue` is a pure
function of two fields the model already holds. `comment_count` needs the comment
store, and a model reaching into storage would invert the dependency — storage
imports models today, not the other way round. So the derivation lives in storage
and the model just carries the number.

**Alternative rejected — incrementing a stored counter when a comment is added.**
One more thing to keep correct, and it goes wrong silently. Deriving it is O(1)
against a per-task index and cannot be wrong.

**Alternative rejected — letting the frontend count.** That is one extra request
per card on every board load.

## Decision 14 — Delete events are recorded, superseding the cascade

**Supersedes the activity half of Decision 12.** Comments still cascade; activity
no longer does, and `DELETE` now writes a `deleted` entry.

**What changed my mind.** The original exclusion was not arbitrary — it argued
that activity was reachable *only* through `GET /tasks/{id}/activity`, which
`404`s once the task is gone, so retained rows would be unreadable by
construction and would simply leak. That was correct given a per-task-only API.
Adding `GET /activity` removed the premise. The same reasoning that justified
dropping the rows now requires keeping them: they are readable, and a history
that silently forgets deletions is not a history.

Worth recording plainly: this is a decision **reversed**, not a decision defended.
The brief allows "delete event recorded **or** intentionally excluded with an
explanation", and the exclusion would still have passed. It stopped being an
honest scope cut the moment the feed existed.

**Consequences:**

- `_activity` becomes one flat append-only list rather than a dict keyed by task.
  There is no per-task bucket to put a deletion in once the task is gone. Per-task
  reads filter the list — O(n), which for an in-memory learning project is cheaper
  than keeping an index correct.
- Entries carry `task_title`, snapshotted at write time. The feed outlives its
  tasks, so it cannot look the name up later. A rename therefore leaves older
  entries under the old name, which is what was true when they were written.
- `GET /tasks/{id}/activity` still `404`s for a deleted task — the sub-resource
  goes with the resource. `GET /activity?task_id=…` returns `[]` instead, because
  a log is not a sub-resource.

**Alternative rejected — a `deleted_at` tombstone on the task.** Keeps the task
row so its sub-resources still resolve, but then every list, filter and count has
to remember to exclude tombstones, and forgetting once shows deleted tasks on the
board. Soft delete is a larger change than the feature needs.

**Alternative rejected — an unbounded feed.** The log only ever grows. `limit`
defaults to 50 and is capped at 200 by FastAPI's own validation, so an
out-of-range value is a `422` rather than a slow response.

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
- **`requirements.txt` cut from 67 pinned packages to 8.** It was a `pip freeze`
  of a much larger environment — Flask, SQLAlchemy, pandas, matplotlib,
  scikit-learn, xgboost, reportlab, APScheduler — none of which this project
  imports. It was also UTF-16 encoded, which is why an earlier grep for those
  package names came back empty and the pollution was missed the first time.
  Replaced with the eight direct dependencies, in UTF-8, and verified by
  installing into a fresh virtualenv and running the suite there: 32 packages
  resolved, 110 tests passed.
- **Two flawed timestamp assertions fixed** — one flaky, one that could not fail.
  See [verification.md](verification.md) §6.

## Explicitly out of scope

Recurring due dates · reminders and notifications · tag rename/merge · tag
colours · per-user "my overdue tasks" · saved filter presets · bulk re-tagging ·
timezone-aware per-user overdue calculation · fuzzy or ranked search · search
result highlighting · pagination · comment editing and deletion · threaded
replies · @mentions · soft delete / undo · activity retention limits · real users
and authentication (comment authors are free text, and the API has no identity of
any kind).

*(A board-wide activity feed was on this list until Decision 14 moved it into
scope.)*
