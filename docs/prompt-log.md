# Prompt Log

**Full document: [midcourse/prompt-log.md](midcourse/prompt-log.md)**

## What it contains

22 prompts (P0–P21), at least three per feature, each with what the assistant
returned and what was **accepted, edited, or rejected**. Abridged to the
decisions rather than pasted as transcripts.

- **The weak prompt rewritten:** P1 — `"Add due dates to the task tracker."`
  rewritten to specify the type, the definition of overdue, where the rule
  lives, the boundary cases, the query-parameter shape, and the files it was
  allowed to touch.
- **Rejections worth reading:** a normalised tag schema (P5), a `/tasks/search`
  endpoint (P11), tokenised OR matching (P12), retaining orphaned activity rows
  (P16), a `deleted_at` tombstone (P19).
- **Where asking beat instructing:** P7 surfaced the tag-dropdown one-way door
  by being phrased as a question; P17 asked which tests would still pass if the
  rule they covered were broken, and found one that could not fail.
