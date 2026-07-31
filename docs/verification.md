# Verification

**Full document: [midcourse/verification.md](midcourse/verification.md)**

## What it contains

| Section | Evidence |
|---|---|
| 1. Baseline | 24 passing on `master` before branching |
| 2. Backend tests | growth table 24 → 41 → 57 → 70 → 109 → 110 → **122** |
| 3. Manual browser checks | per-feature tables; values read from the live DOM |
| 4. Behaviour contract | both refactors, before/after, **byte-identical** |
| 5. Break Tests | **16**, all caught, all files restored |
| 6. A flaky test | traced to an 8ms system clock, measured not guessed |
| 7. Bugs found | 7, including a latent `PATCH`-breaker and an XSS hole |

Break Tests cover the overdue boundary, the `Done` exemption, tag dedup and
filtering, search case-sensitivity and trimming, per-field activity entries,
404-vs-empty, `updated_at` refresh, value truncation, delete events, and feed
ordering and limits.
