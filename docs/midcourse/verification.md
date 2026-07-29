# Verification

Evidence that the four features work: baseline, backend suite, manual browser
checks, the behaviour contract across both refactors, Break Tests, and a flaky
test tracked to its root cause.

Environment: FastAPI + Uvicorn on `:8000`, `frontend/index.html` served as a
static file, Python 3.10 venv, Windows.

---

## 1. Baseline (before any change)

Run on `master` at `8c547b4` with the Module 3 working tree, before branching:

```
$ python -m pytest -q
........................                                                 [100%]
24 passed, 2 warnings in 0.12s
```

**24 passing.** That is the number every later run is measured against.

---

## 2. Backend test results

| Stage | Command | Result |
|---|---|---|
| Baseline | `pytest -q` | 24 passed |
| After Feature 1 backend, before new tests | `pytest -q` | 24 passed (no regression) |
| After Feature 1 tests | `pytest -q` | **41 passed** (+17) |
| After Feature 2 tests | `pytest -q` | **57 passed** (+16) |
| After the frontend refactor | `pytest -q` | **57 passed** |
| After Feature 3 (search) | `pytest -q` | **70 passed** (+13) |
| After Feature 4 backend, before new tests | `pytest -q` | 70 passed (no regression) |
| After Feature 4 tests | `pytest -q` | **109 passed** (+39) |
| After the second frontend refactor | `pytest -q` | **109 passed** |
| After fixing a flaky pre-existing test | `pytest -q` | **110 passed** (+1) |

```
$ python -m pytest -q
..............................................................................
................................                                         [100%]
110 passed, 3 warnings in 0.91s
```

**86 new tests**, well above the required 4:

| File | Tests | Covers |
|---|---:|---|
| `tests/test_tasks.py` | 70 | CRUD, validation, transitions, due dates, tags, search |
| `tests/test_comments.py` | 23 | comment CRUD, validation, scoping, `comment_count` |
| `tests/test_activity.py` | 16 | activity entries, value formatting, cascade |
| `tests/test_health.py` | 1 | health endpoint (pre-existing) |

The three warnings are pre-existing Starlette deprecations, unrelated to this
work.

### What the new tests cover

**Due dates (17)** — valid date accepted and echoed · absent date defaults to
null · malformed `07-29-2026` → 422 · impossible `2026-02-30` → 422 · past date
is overdue · **due today is not overdue** · **Done + past date is not overdue** ·
PATCH updates date and recomputes · PATCH null clears · completing an overdue
task clears the flag but keeps the date · unrelated PATCH preserves the date ·
`?overdue=true` / `=false` / omitted · combined with `priority` · no matches
returns `200 []` · `?overdue=maybe` → 422.

**Tags (16)** — created and echoed · defaults to `[]` · whitespace trimmed ·
blank tag → 422 · 25-character tag → 422 · 11 tags → 422 · non-string → 422 ·
case-insensitive dedup keeps first spelling · PATCH replaces wholesale · PATCH
null clears · unrelated PATCH preserves tags · rejected PATCH leaves the task
untouched · filter by tag · filter is case-insensitive · unknown tag returns
`200 []` · `?tag=…&overdue=true` combined.

**Search (13)** — matches title case-insensitively · matches a fragment inside a
word · matches description · does **not** match assignee · does **not** match
tags · no matches returns `200 []` · empty `q` returns everything · whitespace-only
`q` returns everything · query is trimmed · query is literal, not a pattern
(`?q=.*`) · combined with tag + overdue · combined with priority · handles tasks
with no description.

**Comments (23)** — created and echoed · author optional · blank author stored as
null · body and author trimmed · blank body → 422 · whitespace-only body → 422 ·
missing body → 422 · 2001 chars → 422 · exactly 2000 chars accepted · 81-char
author → 422 · unknown field → 422 · comment on unknown task → 404 · listed oldest
first · empty list for a new task · list on unknown task → 404 · rejected comment
leaves the thread intact · comments scoped to their own task · `comment_count`
starts at 0 · reflects the count · present on `GET /tasks` · survives an unrelated
PATCH · commenting does not change `updated_at` · delete cascades.

**Activity (16)** — `created` entry on task creation · unknown task → 404 · one
entry per changed field · records before and after · re-sending the current value
records nothing · empty PATCH records nothing · rejected PATCH records nothing ·
newest first · enums recorded by value · dates by ISO string · tag lists
comma-joined · cleared tags record `null` · long values truncated at 80 ·
`commented` entry on comment · scoped to its own task · delete cascades.

---

## 3. Manual browser checks

Board loaded against the live API. Values below were read out of the live DOM,
not from a screenshot.

### Feature 1

| Check | Expected | Observed |
|---|---|---|
| Card, due 3 days ago | red overdue pill | `Overdue · Jul 26`, `.is-overdue` present |
| Card, due **today** | plain pill, not red | `Due Jul 29`, `.is-overdue` absent |
| Card, due in 5 days | plain pill | `Due Aug 3` |
| Card, no due date | no pill | `null` |
| `Done` card, due 3 days ago | plain pill, **not** overdue | `Due Jul 26`, not flagged |
| Date rendering | no off-by-one | `2026-07-26` → `Jul 26` |
| `Overdue only` on | only overdue, columns stay | 1 card, `1 overdue task`, 3 columns |
| `Overdue only` off | everything returns | 5 cards, `5 tasks` |
| Edit → due date prefilled | ISO value in date input | `2026-07-26` |
| Edit → push date to future | pill flips to plain | `Due Aug 8`, no longer overdue |

### Feature 2

| Check | Expected | Observed |
|---|---|---|
| Chips on cards | one chip per tag | `backend`, `urgent` |
| Tag dropdown | all tags, sorted, deduped | `backend, frontend, planning, urgent` |
| Filter `planning` | only that task | 1 card, `1 task tagged "planning"` |
| **Dropdown after filtering** | full vocabulary retained | all 4 still listed |
| `planning` + `Overdue only` | no matches, board intact | 0 cards, 3 columns, 3 empty states |
| Create with 11 tags | 422 shown on the field | `at most 10 tags allowed`, modal stayed open |
| `Docs, docs,  review , ` | dedup + trim + drop empty | chips `Docs`, `review` |
| Edit → tags prefilled | comma-joined | `alpha, beta` |

### Feature 3

| Check | Expected | Observed |
|---|---|---|
| Type `database` (8 keystrokes) | debounced to one board request | `["/tasks?q=database", "/tasks"]` — 1 board + 1 vocabulary |
| Search matches description | `postgres` finds the task by its body | 1 card, `1 task matching "postgres"` |
| Stack search + tag + priority | all three apply, all three named | 2 cards, `2 tasks matching "the", High priority, tagged "backend"` |
| Add `Overdue only` on top | narrows to one | 1 card, summary names all four filters |
| Tag dropdown while filtered | full vocabulary retained | all 5 tags still listed |
| Changing priority | does not reset the tag | tag still `backend` |
| Narrow to nothing | board intact, no error | 0 cards, 3 columns, 3 empty states, `No tasks matching "zzzz", …` |
| `Clear` | resets all four controls | `q=""`, `priority=""`, `tag=""`, `overdue=false`, 5 cards, button hides |
| Search box focus | survives re-render while typing | focus retained |

### Feature 4

| Check | Expected | Observed |
|---|---|---|
| `Details` on a task with history | timeline newest first, per field | `Assignee: none → carol`, `Priority: Low → Medium`, `Status: InProgress → Done`, `Status: ToDo → InProgress`, `Created Write the API docs` |
| Two-field PATCH | two separate entries | `priority` and `assignee` logged separately |
| Null value in the log | reads as `none`, not blank | `Assignee: none → carol` |
| Task with no comments | empty state | `No comments yet.` |
| Post a comment | appears immediately, body cleared, author kept | `dana` / `Docs reviewed, ready to publish.`, author field still `dana` |
| Activity after commenting | `commented` entry on top | `dana commented: Docs reviewed, ready to publish.` |
| Card badge after commenting | updates with no reload | `💬 1` |
| Blank comment | blocked client-side | `A comment needs some text.`, **0 requests** |
| 2001-character comment | server 422 surfaced, thread intact | `comment body must be at most 2000 characters`, existing comment still shown |
| Comment with no author | renders as `Anonymous` | `["dana", "Anonymous"]` |
| Escape / backdrop click | closes, restores page scroll | closed, `body.style.overflow` back to `""` |
| Dialog size | fits without page scroll | 627×608 in an 820px viewport, no horizontal scroll |

Console was clean (no errors or warnings) across all of the above.

---

## 4. Behaviour contract — before and after the refactor

The refactor (`1645855`) replaced seven near-identical compare-and-set blocks in
`handleTaskSubmit` with one field-descriptor list. Outgoing requests were
captured by wrapping `window.fetch`, so the contract is checked on what actually
goes over the wire.

| # | Contract | Before | After |
|---|---|---|---|
| 1 | Blank title blocks submit client-side | 0 requests, `Title is required` | **same** |
| 2 | Create sends all seven fields | `POST /tasks` with all 7, assignee trimmed | **same** |
| 3 | Editing one field PATCHes only that field | `PATCH {"priority":"Low"}` | **same** |
| 4 | Saving with no edits sends nothing | 0 requests, modal closes | **same** |
| 5 | Unrelated edit preserves tags + due date | chips `alpha, beta`, `Due Dec 1` | **same** |

Captured after the refactor:

```json
{"method":"POST","url":"/tasks","body":{"title":"Contract check",
 "description":"created by contract test","status":"ToDo","priority":"High",
 "assignee":"alice","due_date":"2026-12-01","tags":["alpha","beta"]}}

{"method":"PATCH","url":"/tasks/06d8…6a0","body":{"priority":"Low"}}
```

`pytest`: 57 passed before the refactor, 57 passed after.

### Second refactor — one shared modal shell

The second refactor (`f5d7158`) collapsed the task modal and the new details
panel onto a single `createModal` controller. Each had carried its own copy of
the shell behaviour, including its own document-level Escape listener.

Captured the same way, in two halves. **Both came back byte-identical.**

| # | Contract | Before | After |
|---|---|---|---|
| M1 | New Task opens empty, page locks | open, fields blank, `overflow: hidden` | **same** |
| M2 | Escape closes and restores scroll | closed, `aria-hidden=true`, `overflow: ""` | **same** |
| M3 | Backdrop click closes | closed, scroll restored | **same** |
| M4 | Details opens and loads, other modal untouched | 2 comments, 3 activity entries, task modal still closed | **same** |
| M5 | Escape closes details, clears the draft | closed, comment body `""` | **same** |
| R1 | Blank title blocks submit | 0 requests, `Title is required` | **same** |
| R2 | Create sends all seven fields | `POST /tasks` with 7 fields, assignee trimmed, trailing comma dropped | **same** |
| R3 | Edit prefills; one change PATCHes one field | `PATCH {"priority":"Low"}` | **same** |
| R4 | Saving with no edits writes nothing | 0 writes, modal closes | **same** |
| R5 | Anonymous comment omits `author` | `POST {"body":"contract comment"}` | **same** |
| R6 | Named comment includes `author` | `POST {"body":"named comment","author":"zoe"}` | **same** |
| R7 | Badge reflects the new count | `💬 2` | **same** |

`pytest`: 109 passed before the refactor, 109 passed after.

---

## 5. Break Tests

Each Break Test deliberately breaks one rule and confirms the test that guards it
actually fails. A test that passes against broken code is not a test. All four
were reverted immediately and the full suite re-run.

### Break 1 — off-by-one on the overdue boundary

`app/models.py`, `due_date < today_utc()` → `due_date <= today_utc()`

```
tests/test_tasks.py::test_due_today_is_not_overdue
>       assert response.json()["is_overdue"] is False
E       assert True is False
1 failed
```

Caught. A task due today would have been marked overdue.

### Break 2 — remove the `Done` exemption

`app/models.py`, deleted `if status == TaskStatus.DONE: return False`

```
tests/test_tasks.py::test_done_task_with_past_due_date_is_not_overdue
>       assert response.json()["is_overdue"] is False
E       assert True is False
1 failed
```

Caught. Finished-but-late work would have stayed flagged forever.

### Break 3 — drop case-insensitive tag dedup

`app/models.py`, removed the `if key in seen: continue` guard

```
tests/test_tasks.py::test_create_task_deduplicates_tags_case_insensitively
E       AssertionError: assert ['Bug', 'bug', 'BUG', 'ui'] == ['Bug', 'ui']
E         At index 1 diff: 'bug' != 'ui'
1 failed
```

Caught, with a diff that names the exact regression.

### Break 4 — make the tag filter case-sensitive

`app/storage.py`, dropped `.casefold()` from both sides of the comparison

```
tests/test_tasks.py::test_list_filter_by_tag_is_case_insensitive
E       assert 0 == 1
E        +  where 0 = len([])
1 failed
```

Caught. `?tag=BUG` would have silently returned nothing for a task tagged `Bug`.

### After restoring all four

```
57 passed, 2 warnings in 0.34s
```

### Breaks 5–12 — features 3 and 4

Run by a script that restores each file in a `finally` block and refuses to
start unless every target is already pristine. (The first version of this
script, written for Breaks 1–4, had no `finally` and left `models.py` broken
when a subprocess call failed — see prompt-log P10.)

| # | Rule broken | Change | Guarding test | Caught |
|---|---|---|---|---|
| 5 | Search is case-insensitive | dropped `.casefold()` from both sides | `test_search_matches_title_case_insensitively` | ✅ `assert [] == ['Ship Release Notes']` |
| 6 | Search trims the query | `q.strip().casefold()` → `q.casefold()` | `test_search_with_whitespace_only_query_returns_every_task` | ✅ `assert 0 == 2` |
| 7 | Search excludes tags | added tags to the match | `test_search_does_not_match_tags` | ✅ `assert [{…}] == []` |
| 8 | One entry per changed field | collapsed to one entry per request | `test_patch_records_one_entry_per_changed_field` | ✅ `assert ['priority, assignee'] == ['assignee', 'priority']` |
| 9 | Unchanged fields log nothing | `if before != after` → `if True` | `test_patch_that_resends_the_current_value_records_nothing` | ✅ `assert ['updated', …] == ['created']` |
| 10 | Unknown task is 404, not `[]` | dropped the existence check | `test_list_comments_on_unknown_task_returns_404` | ✅ `assert 200 == 404` |
| 11 | PATCH refreshes `updated_at` | reused the old timestamp | `test_patch_refreshes_updated_at` | ✅ both timestamps identical |
| 12 | Activity values are truncated | removed the truncation | `test_long_values_are_truncated_in_the_log` | ✅ `assert 500 == 80` |

```
BREAK 8 — Activity collapses to one entry per request
  test   : test_patch_records_one_entry_per_changed_field
  result : 1 failed, 1 warning in 0.14s
  | >       assert sorted(e["field"] for e in updates) == ["assignee", "priority"]
  | E       AssertionError: assert ['priority, assignee'] == ['assignee', 'priority']
  | E         At index 0 diff: 'priority, assignee' != 'assignee'
```

```
All files restored byte-for-byte.
AFTER RESTORE: 110 passed, 3 warnings in 0.91s

Caught 8 of 8 breaks.
```

`git status` was clean afterwards, confirming nothing was left modified.

---

## 6. A flaky test found by running the suite repeatedly

`test_patch_partial_update_keeps_other_fields` asserted
`updated_at != created_at` on a request completing in well under a millisecond.
It failed intermittently. Rather than retry until green, the mechanism was
measured:

```
$ python -c "from datetime import datetime, timezone; \
             print(len({datetime.now(timezone.utc) for _ in range(20000)}))"
2
```

**20,000 calls to `datetime.now()` returned two distinct values** — this machine's
wall clock advances about every 8ms. Probing 300 create-then-patch pairs directly:

```
runs                            : 300
updated_at identical            : 189  (63% -> test fails)
gap microseconds min/median/max : 0 / 0 / 10585
```

So the assertion was close to a coin flip. It is **pre-existing** — it fails at
`c2448b8`, before this branch's second half — but the rate rose as the suite grew
(0/12 runs at baseline vs 5/12 at `f5d7158`), so it was fixed here.

The same root cause had produced the opposite symptom in a test written for
Feature 4: `test_commenting_does_not_change_the_task_updated_at` asserted the
timestamp was *equal*, which held automatically because the clock had not moved.
It would have passed even if commenting did stamp the task — a test that could
not fail.

Both now wait out a clock tick, and the "did it advance?" assertion moved into its
own test rather than riding along in one about field preservation. Break 11 above
confirms the new test actually fails when `updated_at` stops being refreshed.

**0 failures in 15 consecutive full runs** after the fix.

---

## 7. Bugs found and fixed during verification

1. **`PATCH` would have broken entirely.** `storage.update_task` rebuilt tasks
   via `TaskResponse(**existing.model_dump())`. `model_dump()` includes computed
   fields and `TaskResponse` is `extra="forbid"`, so introducing `is_overdue`
   would have made every update 500. Found by reading the storage layer before
   adding the field; fixed by rebuilding from `TaskResponse.model_fields`.
2. **Tag dropdown was a one-way door.** Built from the filtered board response,
   so selecting a tag removed every other option. Fixed with a separate
   unfiltered request for the vocabulary.
3. **Date off-by-one.** `new Date("2026-07-26")` parses as UTC midnight and
   renders as Jul 25 west of Greenwich. Fixed by splitting the ISO string and
   constructing a local date.
4. **Unescaped card HTML.** `task.title` went straight into `innerHTML`. Fixed
   before adding user-controlled tags to the same template.
5. **Two flawed timestamp assertions.** One flaky, one that could never fail —
   see section 6.
6. **A search box that would have fired two requests per keystroke.** Typing an
   eight-letter word issued 16 requests before the input was debounced; one
   afterwards.
7. **`requirements.txt` declared 67 packages for a project that imports four.**
   It was a `pip freeze` of an unrelated environment (Flask, SQLAlchemy, pandas,
   matplotlib, scikit-learn, xgboost, …), saved as UTF-16 — which is why an
   earlier `grep` for those names returned nothing and the problem was dismissed
   as a false report. Found by `cat`-ing the file rather than searching it.

   Rebuilt from the actual imports and verified rather than assumed:

   ```
   $ python -m venv /tmp/clean && /tmp/clean/Scripts/pip install -r requirements.txt
   $ /tmp/clean/Scripts/python -m pytest -q
   110 passed, 3 warnings in 0.93s
   ```

   32 packages resolved (down from 67 declared), suite green on a machine that
   had never seen this project.
