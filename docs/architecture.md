# Architecture — Context Strategy Comparison Log

The same one-page architecture-document task was run three times against this
repository, varying only the context supplied. This log compares the outputs,
records which was adopted, and states the rule taken from the exercise.

The three drafts are kept unedited for comparison:

- [architecture-A.md](architecture-A.md) — minimal context
- [architecture-B.md](architecture-B.md) — structured context (`AGENTS.md` plus
  the `README.md` file listing)
- [architecture-C.md](architecture-C.md) — targeted context (`app/main.py`,
  `app/models.py`, `app/storage.py`, and nothing else)

## 1. Strategy comparison

| | **A — minimal context** | **B — structured context** | **C — targeted context** |
|---|---|---|---|
| **Context supplied** | A one-line task description; free rein to inspect the repo | Two documents, no source files | Three source files, no documents |
| **What it got right** | Complete coverage of all six sections. The only draft to describe frontend behaviour (escaping, filter delegation) and the runtime stack. Noted that `settings` is imported but unused | **The only draft to state the six-pair transition allow-list and the full null-clearing table.** Strongest on business rules — overdue edge cases, activity-truncation nuance, delete semantics, activity limits | Strongest request flow: uuid assignment, a single timestamp reused for both `created_at` and `updated_at`, null-description normalisation. Exact field limits. Most disciplined about the boundary of its own knowledge |
| **What it got wrong or missed** | Asserted that validators raising `ValueError` "become 422" as though the repo said so — that is framework behaviour, stated nowhere in the code. **Methodologically compromised:** written in a session that had already read these files repeatedly, so it does not test minimal context at all | Weakest request flow — no summary contains internal mechanics. **Propagated a stale fact:** carried `AGENTS.md`'s claim that Docker evidence rests on CI, which had already been disproved by building the image locally. Inherited the drift silently | **Missed the status-transition pairs entirely** — the app's most distinctive business rule — because `app/business_rules.py` was not in the anchor set. No versions, no frontend, no tests, no CI or container detail |
| **Best suited for** | Broad orientation with repo access, when one document must cover everything and the read cost is acceptable | Onboarding, rules and conventions questions, policy lookups — anything answered by *what the system guarantees* rather than *how it does it*. Cheapest of the three: two files | Correctness work — debugging, changing a subsystem, verifying a behavioural claim. Anything where being wrong costs more than being incomplete |

**The sharpest single comparison:** C read three source files and still could not
say which status transitions are allowed. B read no source at all and produced
the complete table. The determining factor was not how much context was
supplied, but whether it included the file that owns the rule.

## 2. Verdict

**Adopted: B as the backbone, with C's request flow grafted in. A excluded as
evidence.**

An architecture document is read overwhelmingly for what the system guarantees —
which transitions are legal, what clearing a field does, when a task counts as
overdue. B covered those exhaustively from two files, while C, despite reading
real source, could not answer the first question at all; that settles the base
document. But B's request flow is unusable, and that is precisely C's strongest
section, so the mechanics are taken from C. A is excluded not for being worse but
for being inadmissible: it was produced by a session already saturated with this
repository, so it tests nothing about minimal context, and its one distinctive
error — stating framework behaviour as repository fact — is exactly the failure
the other two avoided. The lasting lesson belongs to B's stale Docker claim: a
curated summary is only as fresh as its last update, and when it has drifted it
misleads confidently rather than failing loudly.

Two practical riders:

- **Anchor sets must be chosen by which file owns the rule**, not by which files
  sound central. C's entire gap traces to omitting one 44-line file.
- **Structured context needs a freshness check.** B reproduced a claim that a
  single `docker build` had already disproved.

## 3. Context-engineering rule

> For orientation tasks — onboarding, architecture overviews, questions about
> rules and conventions — I use **structured context** (`AGENTS.md` plus file
> summaries), because curated documents state business rules exhaustively at a
> fraction of the read cost, and rules are what those tasks actually need. For
> correctness tasks — debugging, changing a subsystem, or verifying a
> behavioural claim — I use **targeted context** anchored on the files that
> *own* the logic, because only source settles mechanics, and a summary that has
> drifted will mislead silently rather than fail loudly.

## Limits of this comparison

- **Strategy A is not a valid control.** All three drafts were produced in one
  long session that had already inspected the repository many times. B and C
  were constrained to declared context and largely held to it; A was not, and
  benefited from accumulated knowledge it did not declare. A genuine
  minimal-context run needs a fresh session.
- **One trial each.** No repetition, so differences between drafts may reflect
  drafting variation as well as context strategy.
- **The task was documentation, not code change.** These findings describe which
  context suits *writing about* a system; they do not establish which suits
  modifying one.
