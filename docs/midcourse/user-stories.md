# User Stories — Mid-Course Project

Two features, both visible in the Kanban UI:

1. **Due dates + overdue filter**
2. **Tags / labels**

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
