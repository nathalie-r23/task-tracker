# User Stories — Mid-Course Project

Four features, all visible in the Kanban UI:

1. **Due dates + overdue filter**
2. **Tags / labels**
3. **Search + combined filters**
4. **Task comments + activity log**

Features 1 and 2 are the two the brief asks for; 3 and 4 were built afterwards
from the same table, on the same workflow.

Each story has acceptance criteria written before implementation. Stories marked
**AI assumption corrected** record a default the assistant proposed that was wrong
for this product and was changed deliberately.

---

## Feature 1 — Due dates + overdue filter

### F1-S1 — Give a task a deadline

> As someone planning a sprint, I want to put an optional due date on a task so
> that I can tell at a glance what is time-bound and what is not.

**Acceptance criteria**

- The task modal has a `Due date` field using a native date picker.
- Leaving it empty creates a task with `due_date: null`; the card shows no date.
- A saved due date appears on the card as `Due <Mon D>`.
- `POST /tasks` accepts `due_date` as an ISO `YYYY-MM-DD` string.
- A malformed date (`07-29-2026`) or an impossible one (`2026-02-30`) is
  rejected with `422` and the error is shown under the Due date field.

### F1-S2 — See what is late

> As someone working a board, I want overdue tasks to stand out so that I fix
> the slipping work first.

**Acceptance criteria**

- A task whose due date is in the past shows a red `Overdue · <Mon D>` pill and
  a red left border on the card.
- `GET /tasks` returns `is_overdue` on every task.
- `is_overdue` is derived on read, never stored, so a task becomes overdue when
  the date rolls over without anything having to update it.

### F1-S3 — Not be nagged about work that is finished or still has time

> As someone using the board, I want "overdue" to mean "needs attention now" so
> that the red pills stay meaningful.

**Acceptance criteria**

- A task due **today** is **not** overdue — the whole day is still available.
- A `Done` task is **never** overdue, even if it was finished after its date.
- Moving an overdue task to `Done` clears the flag while keeping the due date.

> **AI assumption corrected.** The assistant's first cut of the rule was
> `due_date <= today` with no status check — so anything due today was instantly
> red, and finished-but-late work stayed red forever. Both were changed: strict
> `<` for the boundary, and an explicit `Done` exemption. The two Break Tests in
> [verification.md](verification.md) exist specifically to stop either from
> regressing.

### F1-S4 — Filter the board down to what is late

> As someone triaging, I want to hide everything that is not overdue so that I
> can work the backlog of late items.

**Acceptance criteria**

- An `Overdue only` toggle sits in a filter bar above the board.
- With it on, only overdue tasks are shown and the count reads `N overdue tasks`.
- All three columns stay visible, showing their empty state where relevant.
- `GET /tasks?overdue=true` returns only overdue tasks; `overdue=false` returns
  only the rest; omitting it returns everything.
- `?overdue=maybe` is rejected with `422`.
- The filter composes with `status` and `priority`.

> **AI assumption corrected.** The assistant proposed filtering the already
> fetched array in the browser. That would have meant two copies of the overdue
> rule — one in Python under test, one in JavaScript not under test — free to
> drift. The toggle calls the API instead, so the board and the test suite are
> exercising the same rule.

---

## Feature 2 — Tags / labels

### F2-S1 — Label a task

> As someone organising work, I want to put short tags on a task so that I can
> group related work across columns.

**Acceptance criteria**

- The modal has a comma-separated `Tags` field showing the limit inline.
- Tags render as chips on the card, next to the due date pill.
- `POST /tasks` accepts `tags` as a list of strings and defaults it to `[]`.
- Surrounding whitespace is trimmed: `"  backend  "` stores as `"backend"`.
- A trailing comma in the input is ignored rather than sent as a blank tag.

### F2-S2 — Be stopped from creating junk tags

> As someone maintaining the board, I want tag input validated so that the tag
> list does not fill up with blanks, essays, and near-duplicates.

**Acceptance criteria**

- A blank or whitespace-only tag is rejected with `422`.
- A tag longer than 24 characters is rejected with `422`.
- More than 10 tags on one task is rejected with `422`.
- A non-string tag (`[123]`) is rejected with `422`.
- Rejected input leaves the existing task untouched and the modal open with the
  error under the Tags field.

### F2-S3 — Not have case turn one tag into three

> As someone typing quickly, I want `Bug`, `bug` and `BUG` treated as one tag so
> that the tag list does not fragment.

**Acceptance criteria**

- `["Bug", "bug", "BUG", "ui"]` is stored as `["Bug", "ui"]`.
- The first spelling the user typed is the one kept.
- Filtering is case-insensitive: `?tag=BUG` finds a task tagged `Bug`.

> **AI assumption corrected.** The assistant's version lower-cased every tag on
> the way in, so a user who typed `API` got back `api`. Silently rewriting what
> someone typed is a poor trade for a canonical form nobody asked for. Tags are
> now compared case-insensitively but stored exactly as entered.

### F2-S4 — Filter the board by tag

> As someone focusing, I want to show only one tag's tasks so that I can work a
> single workstream.

**Acceptance criteria**

- A `Tag` dropdown in the filter bar lists every tag in use, sorted, deduplicated.
- Choosing one shows only tasks carrying it; the count describes the filter.
- Columns and empty states stay visible.
- It composes with `Overdue only` (`?tag=backend&overdue=true`).
- An unknown tag returns `200` with `[]`, not an error.

> **AI assumption corrected.** The dropdown was first built from the task list
> already on screen. Because that list is what the server filtered, selecting
> `backend` left `backend` as the only remaining option — a one-way door out of
> the filter. The vocabulary now comes from a separate unfiltered request.

### F2-S5 — Keep tags through unrelated edits

> As someone editing a task, I want changing the priority to leave my tags alone
> so that routine edits are not destructive.

**Acceptance criteria**

- `PATCH` with only `priority` leaves `tags` and `due_date` untouched.
- `PATCH` with `tags` replaces the list wholesale.
- `PATCH` with `"tags": null` clears them to `[]`.
- Omitting `tags` from a `PATCH` never changes them.

---

## Feature 3 — Search + combined filters

### F3-S1 — Find a task by typing part of its name

> As someone with a full board, I want to type a few characters and see only the
> matching tasks so that I stop hunting through three columns by eye.

**Acceptance criteria**

- A `Search` box sits in the filter bar and filters as you type.
- Matching is case-insensitive substring: `rele` finds `Ship release notes`.
- `GET /tasks?q=rele` returns the same set the board shows.
- Typing does not fire one request per keystroke — input is debounced.
- A search matching nothing returns `200` with `[]` and the board shows its
  empty states, not an error.

> **AI assumption corrected.** The assistant's first design was a separate
> `GET /tasks/search?q=` endpoint. It could not compose with `status`,
> `priority`, `overdue` or `tag` without re-declaring all four, so "overdue
> backend tasks mentioning migration" would have been unexpressible. Search is a
> fifth query parameter on `/tasks` instead.

### F3-S2 — Search the description as well as the title

> As someone who half-remembers a detail, I want the body text searched too so
> that I can find a task by something written inside it.

**Acceptance criteria**

- `q` matches against `title` **or** `description`.
- `q` does **not** match `assignee` or `tags`.
- Whitespace is trimmed; `?q=` and `?q=%20%20` behave as "no search at all"
  rather than matching nothing.
- The search term is treated as literal text — `?q=.*` matches only tasks
  containing the characters `.*`.

> **AI assumption corrected.** The assistant searched title, description,
> assignee *and* tags. That makes results hard to explain — typing `backend`
> would surface tasks that merely carry a `backend` tag, quietly duplicating the
> tag dropdown sitting next to the box. Search now covers the two free-text
> fields only; tags and assignee have (or can have) their own exact filters.

### F3-S3 — Stack filters instead of choosing between them

> As someone triaging, I want to combine search, tag, priority and overdue so
> that I can narrow to exactly the slice I care about.

**Acceptance criteria**

- The filter bar exposes search, priority, tag and `Overdue only` together.
- All of them apply at once, ANDed: `?q=api&tag=backend&overdue=true&priority=High`.
- The summary line names every active filter, not just the count.
- Changing one filter does not reset the others.
- The tag dropdown still shows the full vocabulary while any filter is active.

### F3-S4 — Get back to the whole board in one click

> As someone who has narrowed too far, I want a single control that clears every
> filter so that I am not resetting four widgets by hand.

**Acceptance criteria**

- A `Clear` button appears in the filter bar only while a filter is active.
- Pressing it resets search, priority, tag and overdue, and refetches.
- With no filters active the summary reads a plain `N tasks`.

---

## Feature 4 — Task comments + activity log

### F4-S1 — Discuss a task where the task lives

> As someone collaborating, I want to leave a comment on a task so that context
> stays attached to the work instead of in a chat thread.

**Acceptance criteria**

- Each card has a `Details` button opening a panel with the task's comments.
- The panel has an author field and a body field; submitting posts the comment
  and it appears immediately, oldest first.
- `POST /tasks/{id}/comments` returns `201` with the created comment.
- `GET /tasks/{id}/comments` returns them in the order they were written.
- Author is optional; an omitted or blank author renders as `Anonymous`.

### F4-S2 — Be stopped from posting nothing, or an essay

> As someone maintaining the board, I want comment input validated so that the
> thread does not fill with blanks and pasted logs.

**Acceptance criteria**

- An empty or whitespace-only body is rejected with `422`.
- A body over 2000 characters is rejected with `422`.
- An author over 80 characters is rejected with `422`.
- Commenting on a task id that does not exist returns `404`.
- A rejected comment leaves the existing thread untouched.

> **AI assumption corrected.** The assistant returned `200 []` when asked for the
> comments of a task that does not exist. That makes a typo'd id look like a task
> nobody has commented on. Unknown task is `404` on every nested route.

### F4-S3 — See what actually happened to a task

> As someone picking up a task, I want a history of what changed so that I do not
> have to ask why it moved or when the date slipped.

**Acceptance criteria**

- The details panel shows an activity timeline, newest first.
- Creating a task records a `created` entry.
- Every changed field on a `PATCH` records its own `updated` entry naming the
  field and its before and after values.
- A `PATCH` that changes nothing records nothing.
- Posting a comment records a `commented` entry.
- `GET /tasks/{id}/activity` returns the same entries.

> **AI assumption corrected.** The assistant logged one entry per `PATCH` with a
> dictionary of changed fields in it. The timeline then rendered as JSON blobs,
> and "when did the priority change?" needed the reader to parse each one. Each
> changed field now gets its own entry, so the log reads as a list of sentences —
> `Priority: Medium → High`.

### F4-S4 — Spot which tasks have discussion without opening them

> As someone scanning the board, I want to see that a task has comments so that I
> know where the conversation is.

**Acceptance criteria**

- A card with at least one comment shows a comment-count badge.
- A card with none shows no badge.
- `GET /tasks` includes `comment_count` on every task.
- The count is correct straight after posting, with no page reload.
- The count never goes stale against the comment store.

### F4-S5 — Not leave orphans behind

> As someone deleting a finished task, I want its comments to go with it so that
> the store does not accumulate unreachable records.

**Acceptance criteria**

- `DELETE /tasks/{id}` removes the task's comments.
- Comments and activity for one task are never returned for another.
- A new task starts with an empty thread and a single `created` entry.

> **Superseded in part.** This story originally said activity was deleted too,
> and justified it: activity was only reachable through
> `GET /tasks/{id}/activity`, which `404`s once the task is gone, so keeping the
> rows would have leaked records nothing could read. That reasoning was sound —
> until `GET /activity` existed. See F4-S6.

### F4-S6 — See that something was deleted

> As someone who cannot find a task, I want the board's history to show that it
> was deleted so that I am not left wondering whether I imagined it.

**Acceptance criteria**

- `DELETE /tasks/{id}` records a `deleted` entry.
- `GET /activity` returns events across every task, newest first.
- A deleted task's entries — including the deletion — remain on that feed.
- `GET /tasks/{id}/activity` still `404`s for a deleted task: the task resource
  is gone, so its sub-resource is too.
- `GET /activity?task_id=…` for an unknown id returns `200 []`, not `404` — a
  log is not a sub-resource, and asking it about a task that no longer exists is
  the normal way to find out what happened.
- Every entry carries `task_title` as it was **at the time**, so the feed is
  readable without the task still existing.
- The feed is capped (`limit`, default 50, max 200) because the log only grows.
- An `Activity` button in the header opens the feed; `deleted` entries are
  struck through.

> **Decision reversed, not defended.** Excluding delete events was the right call
> *given a per-task-only API*. Adding the board-wide feed removed the premise —
> the rows are now readable — so the exclusion became a hole rather than a scope
> cut. The honest response was to reverse it. Recorded as ADR Decision 14
> superseding the cascade half of Decision 12.
