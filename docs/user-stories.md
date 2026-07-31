# User Stories

**Full document: [midcourse/user-stories.md](midcourse/user-stories.md)**

Kept in `docs/midcourse/` because the submission checklist asks for that path;
this pointer exists because the deliverables table names `docs/user-stories.md`.
See [README.md](README.md).

## What it contains

18 stories across the four features (4 / 5 / 4 / 5), each with acceptance
criteria written **before** implementation:

| Feature | Stories | AI assumptions corrected |
|---|---|---|
| 1 — Due dates + overdue filter | F1-S1 … F1-S4 | overdue boundary (`<=` vs `<`, no `Done` check); client-side filtering |
| 2 — Tags / labels | F2-S1 … F2-S5 | tags lower-cased on write; tag dropdown built from the filtered list |
| 3 — Search + combined filters | F3-S1 … F3-S4 | search as a separate endpoint; search covering tags and assignee |
| 4 — Comments + activity log | F4-S1 … F4-S5 | `200 []` instead of `404`; one log entry per request; delete-event exclusion (later reversed) |
