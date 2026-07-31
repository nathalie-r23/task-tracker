# Mini-ADR

**Full document: [midcourse/mini-adr.md](midcourse/mini-adr.md)**

## What it contains

14 numbered decisions, each with the alternatives that were considered and
rejected, plus a "changes made in passing" list and an explicit out-of-scope
list.

The load-bearing ones:

- **D1** `is_overdue` computed on read, not stored — and the `extra="forbid"`
  round-trip trap that would have broken every `PATCH`
- **D4** tags compared case-insensitively but stored as typed; a normalised tag
  table with its own CRUD was rejected as a feature in its own right
- **D7–D8** search as a query parameter, not an endpoint, scoped to title and
  description
- **D10** one activity entry per changed field, not one blob per request
- **D12** comments append-only, so "does deleting a comment delete its log
  entry?" never has to be answered
- **D14** delete events recorded — **reversing** part of D12 once a board-wide
  feed made the premise of the original exclusion false
