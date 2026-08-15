# Documentation Claim-vs-Reality Audit

A project-scoped checklist for the Task Tracker. Verifies that what the docs say
matches what the code does — and reports the gap before anyone decides which side
is wrong.

Optional extension, not a Module 4 required deliverable.

## 1. Name

**doc-claim-audit** — Documentation Claim-vs-Reality Audit

## 2. When to use it

Run this before treating documentation as done:

- After any rewrite of `README.md`, `CLAUDE.md`, or a batch of docstrings
- Before submitting a module deliverable that asserts behaviour (status codes,
  limits, commands)
- After a branch adds infrastructure whose docs describe behaviour nobody has
  executed (Dockerfile, workflows)
- When a doc and a test seem to disagree

Do **not** run it as a code review — it audits claims, not design.

## 3. Inputs required

| Input | Required | Notes |
|---|---|---|
| Target docs | yes | Which files' claims are in scope (e.g. `README.md` + `app/**` docstrings) |
| Branch or diff base | yes | Usually `mid-course-project`; determines what "changed" means |
| Working venv | yes | `venv\Scripts\python.exe` with `requirements.txt` installed — needed to probe behaviour |
| Docker engine | no | Only if image claims are in scope. If unavailable, mark those claims `[VERIFY]` — do not skip silently |
| CI access (`gh` or the Actions tab) | no | Only if the docs claim CI status. Without it, "verified green" stays `[VERIFY]` |

## 4. Steps to follow

1. **Read the index before judging the tree.** Start with `docs/README.md` and
   `CLAUDE.md`. Structure that looks like duplication or cruft is often
   deliberate and explained there.
2. **Enumerate the claims.** List every statement that asserts behaviour: status
   codes, validation outcomes, limits, defaults, file contents, commands. Ignore
   prose that asserts nothing.
3. **Separate checkable from unverifiable.** A claim is checkable if a command or
   probe settles it here and now. Everything else gets `[VERIFY]` plus a note on
   what access would settle it.
4. **Probe, don't read.** Execute the behaviour. Use a throwaway script in the
   scratchpad with `TestClient(app, raise_server_exceptions=False)` — that flag
   matters, or a 500 surfaces as an exception instead of a status code. Record
   output verbatim.
5. **Check that verification steps can fail.** For any CI step or documented
   command that asserts something, ask: would this still pass if the thing it
   checks were deleted? If yes, it is decorative — report it.
6. **Run the suite** (`pytest -q`) before and after; record both counts. A changed
   count the docs don't reflect is itself a finding.
7. **Report before fixing.** Produce the table in §5 and stop. For each
   discrepancy the fix may belong to the docs *or* the code — that choice is the
   user's.
8. **On approval, apply docs-only fixes.** Behaviour changes, CI edits and
   dependency changes each need separate approval (see §6).
9. **Re-run the suite** and report the count. If a fix changed it, update any doc
   stating it — including this audit's own outputs.

## 5. Output format

One row per claim examined:

| Documentation claim | Code or runtime reality | Resolution | Evidence to keep |
|---|---|---|---|

Rules:

- **Quote the claim** with a `file:line` reference — never paraphrase
- **Reality** must be a measurement, not a reading: a status code, a byte count,
  a command's output
- **Evidence to keep** must be reproducible by the user — the command, not a
  summary of it
- Unsettled claims get `[VERIFY]` in Resolution, plus what access would settle them
- Close with a list of **claims checked and found correct** — this is module
  evidence, and it stops the same claims being re-audited

Then, separately: what was fixed, what needs approval, what remains open.

## 6. Safety limits

**May read freely:** `app/`, `tests/`, `frontend/`, `docs/`, `README.md`,
`CLAUDE.md`, `Dockerfile`, `.dockerignore`, `.github/workflows/`,
`requirements.txt`.

**May edit after approval, docs only:** `README.md`, docstrings in `app/`,
`CLAUDE.md`, files under `docs/decisions/`.

**Must not edit:**

- `docs/midcourse/` deliverables — `CLAUDE.md` §7 forbids changing these as a
  side effect of other work
- **Test assertions, to make a doc claim true.** If a claim contradicts a test,
  one of them is wrong — report it, never adjust the assertion to fit the prose
- `requirements.txt`, or any pinned version
- Status-transition rules, the overdue rule, or enum wire values

**Must not run without explicit approval:**

- `git commit`, `git push`, or any history rewrite
- `docker build` / `docker run` — slow, and starting the engine is a
  machine-level action
- `pip install` or anything mutating the venv
- Any edit to `.github/workflows/` — CI changes are riskier than prose changes
- Any change to runtime logic, even to fix a defect the audit found

**Scope discipline:** this workflow reliably surfaces real bugs. That is a known
side effect, not a mandate. Report them; let the user decide whether fixing them
belongs in this pass.

**Never claim** the app has authentication, a database, persistence, deployment
or production hardening. It has none. "Verified" here means the docs match the
code, nothing more.

## Known limitation

This audit verifies claims *someone thought to check*. It has no mechanism for
finding claims the docs never made but should have. Step 2 is where it can
silently under-deliver.
