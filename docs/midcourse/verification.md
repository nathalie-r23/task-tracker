# Verification

Evidence that the two features work: baseline, backend suite, manual browser
checks, the behaviour contract across the refactor, and Break Tests.

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

```
$ python -m pytest -q
.........................................................                [100%]
57 passed, 2 warnings in 0.30s
```

**33 new tests** (17 due dates, 16 tags), well above the required 4. The two
warnings are pre-existing Starlette deprecations, unrelated to this work.

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

---

## 6. Bugs found and fixed during verification

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
