# My AI Coding Playbook

*Personal working rules. Revise when a rule breaks, not when it feels stale.*

## 1. When I reach for AI first

- **Mechanical work spread across many files** — docstrings for 24 functions, a
  README rewrite — because it is a first draft I will rewrite anyway, and a wrong
  sentence is visible.
- **Verification sweeps**, checking documentation claims against a running app,
  because it is tedious at scale and the result is checkable. Five claims here
  survived careful reading and turned out false when executed.
- **Drafting infrastructure** — Dockerfile, CI YAML — because I can confirm the
  result by building and running it rather than by trusting it.

## 2. When I do not reach for AI

- **Anything I cannot verify by running something**, because the failure is
  silent. A `.dockerignore` defect passed CI for weeks: a fresh checkout has no
  bytecode to exclude, so the assertion could not fail.
- **Scope and product decisions** — whether to add auth, whether to cap a field —
  because those are judgements about what the project should be, not facts about
  what it is.
- **Reading a large unfamiliar file to understand it**, because I end up with a
  summary I trust instead of understanding I own.

## 3. My non-negotiables

- I do not let a tool read `.env`, credential files, or anything I have not
  opened myself first. A tool read `.env` during this course and the contents
  were harmless by luck of contents, not by process.
- I do not sign an attestation I have not earned. If I have not read the code,
  the honest answer is "no", not a blank.
- I do not let a tool change pinned dependencies, CI, or `app/` without my
  explicit approval, one change at a time.

## 4. My review rules

- **Before accepting:** if it is a claim about behaviour — a status code, a
  limit, a validation outcome — I run it and record the command. Reading the
  handler is not verification.
- **Before committing:** the full suite passes, and I can say what changed and
  why in one sentence.
- **When AI and I disagree:** whoever can produce a command that settles it
  wins. If neither can, it stays marked `[VERIFY]` rather than being asserted.

## 5. What I am still figuring out

- Whether my review hit-rate comes from the tool or from grading every finding.
  Seven security findings, three graded Valid — I cannot separate the two causes
  without running the same review twice and grading only one.
- Whether I retire `[VERIFY]` markers as fast as I add them. One sat unresolved
  for weeks until the Docker engine finally started.
- How much of a 2160-line file I have to read before I can honestly sign for it.

---

## Decision Card

- For a new feature I reach for: **Cursor** — larger implementation loops across
  several files, where I want to steer edit by edit.
- For a code review I reach for: **Codex App** — desktop review and planning.
  With the caveat that on this project the useful part was grading every finding
  myself: seven came back, three graded Valid.
- For debugging I reach for: **Claude Code** — every real defect I found this
  course came from running something, not reading it.
- For infrastructure I reach for: **general chat to author, a terminal tool to
  verify** — authoring is a reasoning problem, verifying is an execution problem,
  and the second is where the bugs were.
- I will never paste **credential or configuration files, or command output
  containing personal identifiers,** into an AI tool.
- My one rule is: **a claim about behaviour is not verified until I have run it
  and recorded the command.**

## Re-read commitment

I will re-read this playbook on **2026-09-15**, thirty days from today. At that
re-read I will check which rules I actually followed, which I broke and why, and
whether any rule is still here because it sounds right rather than because it
earned its place. A rule I have not applied in thirty days gets deleted or
rewritten.

---

*Last revised: 2026-08-16*
