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

The figures above describe the **mid-course** submission on branch
`mid-course-project`. Module 4 work continues on `ci-setup`, where the suite
stands at **125 tests**.

## Module 4 additions

| Document | What it is |
|---|---|
| [decisions/0001-documentation-verification.md](decisions/0001-documentation-verification.md) | Technical decision note — how documentation claims are verified before publishing (**draft**) |
| [module4/annotated-review-log.md](module4/annotated-review-log.md) | Every Claude review comment categorised Useful / Noise / Wrong |
| [module4/docker-security-log.md](module4/docker-security-log.md) | Non-root, slim base, no baked secrets — **claims pending evidence**, engine would not start locally |
| [checklists/doc-claim-audit.md](checklists/doc-claim-audit.md) | Reusable checklist for running that audit (optional extension, not a required deliverable) |

## Module 5

| Document | What it is |
|---|---|
| [security-review.md](security-review.md) | Read-only security review, AI findings graded Valid / False Positive / Noise, reconciliation and top-3 backlog |
| [governance-retrospective.md](governance-retrospective.md) | What was shared with AI tools, what was received, and three personal usage rules. Observed evidence for one tool; recall for the rest, kept distinct |
| [decisions/comments-feature-plan.md](decisions/comments-feature-plan.md) | Gap analysis of the comments feature against a supplied spec — the feature already exists; `author` is the only delta |
| [architecture.md](architecture.md) | Context-strategy comparison log — three architecture drafts under different context, the verdict, and the rule taken from it |
| [architecture-A.md](architecture-A.md) · [architecture-B.md](architecture-B.md) · [architecture-C.md](architecture-C.md) | The three drafts, kept unedited as the comparison's evidence |

Setup, run and test instructions are in the [root README](../README.md).
