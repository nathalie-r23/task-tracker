# Documentation index

The brief names two locations for these files: the deliverables table lists
`docs/user-stories.md` and friends, while the submission checklist asks for
`docs/midcourse/`. Rather than pick one and hope, the **full documents live in
[`docs/midcourse/`](midcourse/)** and each file also exists at the top level of
`docs/` as a short pointer with a summary of what it contains.

| Requirement | Full document |
|---|---|
| 3–5 user stories per feature, acceptance criteria, AI assumptions corrected | [midcourse/user-stories.md](midcourse/user-stories.md) |
| Decision note, alternatives suggested, what was rejected | [midcourse/mini-adr.md](midcourse/mini-adr.md) |
| ≥3 prompts per feature, one weak prompt rewritten | [midcourse/prompt-log.md](midcourse/prompt-log.md) |
| Baseline, test results, browser checks, behaviour contract, Break Tests | [midcourse/verification.md](midcourse/verification.md) |
| 250–500 word reflection | [midcourse/reflection.md](midcourse/reflection.md) |

## Features covered

The brief asks for two. Four were built, on the same workflow:

1. **Due dates + overdue filter**
2. **Tags / labels**
3. **Search + combined filters**
4. **Task comments + activity log**

## At a glance

- Baseline: **24 tests** · final: **122 tests** (98 new; the brief asks for 4)
- **16 Break Tests**, all caught, every file restored afterwards
- Two refactors, each with a behaviour contract captured before and after and
  verified byte-identical
- Branch: `mid-course-project`

Setup, run and test instructions are in the [root README](../README.md).
