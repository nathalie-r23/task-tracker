# Comments on Tasks — Feature Plan

**Status: the feature is already implemented.** This document is a gap analysis
between a supplied specification and what the repository actually contains, not
a build plan.

## 0. Blocking question — answer this first

**Is the supplied specification a change request, or a description of what was
expected to exist?**

Everything below depends on the answer:

- **If it describes expectations:** no work is needed. The feature is complete
  and covered by 23 tests. Stop here.
- **If it is a change request:** exactly one field differs, and changing it is a
  breaking change to working, tested behaviour. Continue to §1.

This question is placed first deliberately. An earlier draft buried it under
five sections of analysis, which meant a reader absorbed the whole document
before learning whether any of it mattered.

## Specification supplied

| Field | Spec |
|---|---|
| `id` | string UUID |
| `task_id` | string foreign key or task reference |
| `author` | **required string, 1–100 characters** |
| `body` | required string, 1–2000 characters |
| `created_at` | server-generated UTC datetime |

## 1. Data Model

Comment models live in `app/models.py` alongside task models — this repo keeps
all Pydantic models in one file rather than splitting by resource. Two models
exist, following the same `Create`/`Response` split as tasks:

- `CommentCreate` (`app/models.py:185`) — request body, `extra="forbid"`
- `CommentResponse` (`app/models.py:216`) — `id`, `task_id`, `author`, `body`,
  `created_at`

| Field | Spec | Implemented | Match |
|---|---|---|---|
| `id` | string UUID | `str`, server-assigned via `uuid4()` (`app/storage.py:262`) | yes |
| `task_id` | string reference | `str`, taken from the URL path, never the body | yes |
| `author` | **required, 1–100** | **optional, max 80, blank stored as `null`** (`app/models.py:189`, :201-213) | **no — three differences** |
| `body` | required, 1–2000 | required, trimmed, max 2000 (`app/models.py:191-199`) | yes |
| `created_at` | server UTC datetime | `datetime.now(timezone.utc)` (`app/storage.py:266`) | yes |

**The `author` field is the entire delta.** The implementation deliberately
treats a missing or blank author as anonymous. The code comment at
`app/models.py:204` states: *"A blank author is 'anonymous', not a mistake —
only an absurdly long one is worth rejecting."* Three changes would be required:
optional → required, add a 1-character minimum, and raise 80 → 100.

**Storage** (`app/storage.py:18`): comments live in
`_comments: dict[str, list[CommentResponse]]`, keyed by task id and
append-ordered. This differs from the activity log at :23, which is a flat list
*not* keyed by task — the keying is what makes per-task deletion cheap.

**Derived count:** `comment_count` is a plain field on `TaskResponse` stamped at
read time by `_with_comment_count()` (`app/storage.py:60-67`), not a computed
field. The comment at :167 explains why: the model has no way to reach storage.

## 2. API Routes

Both routes are defined in `app/main.py`, not in a separate router — health is
the only extracted router in this codebase.

### `POST /tasks/{task_id}/comments` (`app/main.py:218`)

Request body:

| Field | Required | Rules |
|---|---|---|
| `body` | yes | trimmed, non-blank, max 2000 chars |
| `author` | no | max 80 chars; blank or omitted stored as `null` |

Any other key returns 422 — `CommentCreate` sets `extra="forbid"`.

Response body — **201**, the full `CommentResponse`:

| Field | Type |
|---|---|
| `id` | string (UUID) |
| `task_id` | string |
| `author` | string or `null` |
| `body` | string |
| `created_at` | datetime (UTC) |

Errors: **404** unknown task; **422** validation failure.

Side effect: records a `commented` activity entry but **deliberately does not
touch the task's `updated_at`** (`app/storage.py:276`) — commenting on a task is
not editing it.

### `GET /tasks/{task_id}/comments` (`app/main.py:250`)

No request body. Response — **200**, an array of `CommentResponse` objects,
oldest first.

Errors: **404** unknown task — explicitly *not* an empty array. The docstring at
:252 gives the reasoning: *"a mistyped id should not look like a task nobody has
commented on."*

**Not implemented, apparently deliberately:** no `PATCH`, no `DELETE`, no
pagination. `README.md` documents comments as append-only.

## 3. Tests

`tests/test_comments.py` holds **23 tests**. Style: plain functions taking a
`client` fixture, named as full sentences describing the assertion.

**Happy path (5)**

- `test_create_comment_returns_201_with_full_body`
- `test_list_comments_returns_them_oldest_first`
- `test_list_comments_on_a_new_task_returns_empty_list`
- `test_create_comment_trims_surrounding_whitespace`
- `test_comments_are_scoped_to_their_own_task`

**Validation (8)**

- `test_create_comment_with_blank_body_returns_422`
- `test_create_comment_with_whitespace_only_body_returns_422`
- `test_create_comment_without_body_returns_422`
- `test_create_comment_over_2000_characters_returns_422`
- `test_create_comment_of_exactly_2000_characters_is_accepted`
- `test_create_comment_with_over_long_author_returns_422`
- `test_create_comment_with_unknown_field_returns_422`
- `test_create_comment_on_unknown_task_returns_404`

**Anonymous-author behaviour (2)**

- `test_create_comment_without_author_stores_null`
- `test_create_comment_with_blank_author_stores_null`

Both **would need rewriting** if `author` becomes required — they assert the
opposite of the specification.

**Edge cases (8)**

- `test_list_comments_on_unknown_task_returns_404`
- `test_rejected_comment_leaves_the_existing_thread_untouched`
- `test_new_task_reports_zero_comments`
- `test_comment_count_reflects_the_number_of_comments`
- `test_comment_count_is_present_on_the_list_endpoint`
- `test_comment_count_survives_an_unrelated_patch`
- `test_commenting_does_not_change_the_task_updated_at`
- `test_deleting_a_task_removes_its_comments`

**Tests that would need adding** under a required 1–100 author, matching the
existing boundary style (the suite already tests 2000 and 2001 characters for
`body`):

- `test_create_comment_without_author_returns_422`
- `test_create_comment_with_blank_author_returns_422`
- `test_create_comment_with_single_character_author_is_accepted`
- `test_create_comment_with_exactly_100_character_author_is_accepted`
- `test_create_comment_with_101_character_author_returns_422`

## 4. Frontend Changes

All in `frontend/index.html`, the single 2160-line file with no build step.

**Already present:**

- Comment form at :1082 — `#comment-author` text input, `#comment-body`
  textarea, `#comment-error` banner with `role="alert"`
- Rendering at :1747-1754 — author, timestamp and body, each passed through
  `escapeHtml()`
- Anonymous fallback at :1751 — `comment.author || "Anonymous"`
- Empty state at :1743 — "No comments yet."
- Form reset on success (:1864) and on modal close (:1872)
- Error handling at :1928

**What would change if `author` becomes required** (verified against
`frontend/index.html:1082-1092`):

- **There is no `maxlength` attribute on either input.** One would have to be
  *added* to `#comment-author`, not changed. *(An earlier draft of this plan
  asserted a `maxlength` existed and would need updating. It does not — the
  claim was written without opening the element.)*
- The placeholder at :1085 reads `"Your name (optional)"` and directly
  contradicts a required field.
- The `|| "Anonymous"` fallback at :1751 becomes dead code.
- The form carries `novalidate` (:1082), so browser-native required-field
  handling is off by design; validation would need adding in script.

## 5. Migration Notes

**No storage migration exists or is possible.** Storage is in-process
dictionaries wiped on restart (`app/storage.py:16-23`). There is no database, no
schema and no persisted data.

**But making `author` required is a breaking API change:**

- Existing clients sending only `body` would begin receiving 422
- Two tests assert the current anonymous behaviour and would fail
- The frontend's anonymous fallback becomes unreachable
- `README.md`, `CLAUDE.md` and `AGENTS.md` all document `author` as optional and
  would become wrong

**Deletion behaviour is already decided and tested** (`app/storage.py:238`):
deleting a task removes its comments but **keeps** its activity, including the
`commented` entries. The reasoning at :234 is that comments are only reachable
through a route that 404s once the task is gone, so retaining them would leak
records nothing can read.

## 6. Open Questions

1. **Should anonymous comments be dropped at all?** With no authentication
   (`app/main.py:56-57`), a required author is an unverified free-text field —
   accountability in appearance only. Requiring it may add friction without
   adding trust.
2. **80 or 100 characters?** If `author` stays optional, is a 20-character
   difference worth a breaking change plus test and documentation updates?
3. **Does pagination matter yet?** `GET` returns every comment with no limit,
   unlike `GET /activity`, which caps at 200 (`app/storage.py:348`).
4. **Should the number of comments per task be capped?** Bodies are capped at
   2000 characters, but nothing limits how many comments a task accumulates.
   Related to finding S1 in `docs/security-review.md`.

---

## Files read

`AGENTS.md` · `README.md` · `CLAUDE.md` · `app/models.py` · `app/main.py` ·
`app/storage.py` · `app/business_rules.py` · `tests/test_comments.py` (names and
structure) · `frontend/index.html` (form :1082-1092, rendering :1743-1754,
handlers :1860-1930) · `docs/security-review.md`

## Assumptions to verify

1. **That the specification is a change request.** §0 exists because this is
   unresolved.
2. **The test suite was not run for this document** — read-only. The 23 names
   come from `grep "^def test_"`. The full suite passed at 125 earlier the same
   day.
3. **`frontend/index.html` was read selectively** — roughly 200 of 2160 lines
   around comments. Claims about the submit path are limited to the elements
   inspected.
4. **Character limits** were read from `MAX_AUTHOR_LENGTH = 80`
   (`app/models.py:182`) and the validator at :201-213, not confirmed by
   executing a boundary test.
5. **No implementation code was written and no file under `app/` was modified.**
