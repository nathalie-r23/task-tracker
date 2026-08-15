# Technical Decision Note: Documentation Verification Approach

**Status:** Draft
**Date:** 2026-08-15
**Module:** 4 — Task Tracker
**Scope:** How documentation claims in this repo are checked before being published

---

## 1. Context

Module 4 turned documentation into a deliverable rather than a by-product. In one
branch (`ci-setup`) the repo gained a `Dockerfile`, `.dockerignore`, two GitHub
Actions workflows, Google-style docstrings across 24 public functions, and a full
`README.md` rewrite — 941 insertions against `mid-course-project`.

That created a problem the earlier modules did not have. The code is verified by
125 pytest tests; the documentation was verified by reading it. Those are not
equivalent, and the gap showed up as soon as it was checked:

- `app/main.py`'s module docstring still said "**Module 1** Task Tracker API. Only
  the health endpoint is wired up at this stage — no CRUD, storage, or business
  logic yet." The same file defined ten routes. The docstring commit rewrote every
  other docstring in the file and stepped over this one.
- The same claim was user-facing. `FastAPI(description=...)` carried
  "Module 1 learning project — REST API skeleton", which `/docs` and
  `/openapi.json` rendered to anyone browsing the API.
- `describe_value()` in `app/models.py` documented that any rendered value over 80
  characters is truncated. Measured: a ten-tag list stored a 218-character
  `to_value` with no ellipsis, because the `list`/`tuple` and `date` branches
  return before the length check.
- `update_task()` documented exactly two failure modes, 404 and 422. A third
  existed: `PATCH {"title": null}` returned **500**.
- `docker-verify.yml` asserted that `.dockerignore` exclusions were applied. The
  assertion could not fail — the runtime stage's only source copy is
  `COPY app ./app`, so none of the asserted paths could reach `/app` even with
  `.dockerignore` deleted.

Nothing here was careless writing. Every one of these was plausible prose that
happened to be false, and none of it was catchable by re-reading. The last one is
the sharpest: a verification step that passes unconditionally is worse than no
step, because it manufactures confidence.

## 2. Decision

Treat every documentation claim as a testable assertion, and verify it against
running code before publishing it.

Concretely:

1. **Claims about behavior are checked by executing the behavior.** Status codes,
   validation outcomes, truncation limits and response shapes are confirmed with a
   `TestClient` probe or a `curl` against a running server — not by reading the
   handler.
2. **Claims that cannot be checked from the working copy are marked `[VERIFY]`**
   and left visible in the document. An unverifiable claim stays labelled rather
   than being quietly asserted or quietly deleted.
3. **A verification step must be able to fail.** Any check — CI step or documented
   command — is paired with a positive control proving it discriminates. The
   `docker-verify.yml` "Assert the app itself IS present" step is the pattern; the
   `.dockerignore` step is the counter-example.
4. **Docstrings are held to the same standard as the README.** They are published
   through `/docs` and `/openapi.json`, so they are user-facing documentation, not
   internal comments.
5. **When docs and code disagree, the discrepancy is reported before either is
   changed** — because the fix is sometimes the code, not the prose. The 500 on
   `PATCH {"title": null}` was found as a documentation gap and resolved as a bug.

## 3. Alternatives Considered

**A. Careful review — read the docs against the code.**
Rejected. This is what produced the drift. Every false claim above survived at
least one focused editing pass, including a pass whose entire purpose was
rewriting docstrings in that same file.

**B. Executable documentation (doctest, pytest-examples).**
Rejected for this module. It would mechanically guarantee that documented examples
run, which is a real benefit. But it constrains prose to what a doctest can
express, and adds a dependency — `CLAUDE.md` pins the dependency set and forbids
additions. Worth revisiting if the API surface stabilises.

**C. Enforce documentation checks in CI.**
Deferred, not rejected. A CI job could assert that the OpenAPI `description` does
not contain "skeleton", or that route docstrings list every status code the
handler can return. This is the natural next step, but writing assertions against
prose risks the same vacuous-check failure mode described above, and the pattern
needs to be established manually first.

**D. Document less.**
Rejected. The claims that turned out to be wrong were also the useful ones —
status codes, limits, null semantics. Removing them would remove the value along
with the risk.

## 4. DRAFT - REWRITE IN MY OWN WORDS — Trade-offs

- **Verification costs real time.** Confirming the five claims above meant writing
  a throwaway probe script and running it against the app. That is slower than
  reading, and the cost is paid on every documentation change.
- **It finds bugs, which is both the point and a scope risk.** The 500 was
  discovered by an audit whose brief was documentation. Fixing it meant touching
  `app/models.py` and adding three tests — beyond the stated scope. Verification
  reliably generates work that was not planned for.
- **`[VERIFY]` markers are honest but they accumulate.** The README currently
  carries three. They correctly signal "unconfirmed", but a document with many
  markers starts to read as unfinished, and there is a temptation to clear them by
  deleting rather than checking.
- **Probes are not tests.** The script that measured the 218-character tag value
  lived in a scratch directory and was thrown away. The finding survived; the check
  did not. Only the null-PATCH finding became a permanent regression test.
- **Some claims stay unverifiable — until they don't.** For most of this project
  Docker Desktop would not start (WSL had no distributions installed), so every
  statement about the image rested on CI runs observed elsewhere. That was
  recorded as `[VERIFY]` rather than asserted. **Resolved 2026-08-15:** WSL was
  installed, the engine came up, and the image was built and run locally — at
  which point one of the five checks *failed*. `.dockerignore` was shipping ten
  nested `__pycache__` directories into the image, because its bare patterns
  matched only top-level entries. Neither a code read nor six weeks of green CI
  had surfaced it, since a fresh runner checkout has no bytecode to exclude in
  the first place. The `[VERIFY]` marker was doing real work: it held the
  question open until the one check that could answer it became possible.

## 5. Consequences

**Immediate:**

- Five documentation claims were corrected: the `main.py` module docstring, the
  OpenAPI `description`, the `describe_value` truncation wording, the README
  Docker port instruction, and the `CLAUDE.md` "no Docker/CI" rule that the same
  branch had contradicted.
- One genuine defect was found and fixed. `PATCH {"title": null}` and
  `{"description": null}` returned 500; they now return 422 and 200 respectively,
  matching the three sibling fields that already cleared cleanly. Test count went
  from 122 to 125.
- One CI step is now known to be decorative. `docker-verify.yml`'s `.dockerignore`
  assertion has not been changed — it is harmless, but it is not evidence.

**Ongoing:**

- Documentation changes now carry a verification step, so they are slower.
- Docstrings that describe status codes are load-bearing: they will be checked
  against the handler, and a mismatch is treated as a defect in one or the other.
- The repo has a precedent for reporting a discrepancy before fixing it, which
  keeps the choice between "fix the docs" and "fix the code" explicit.

**Not consequences.** This does not make the app production-ready. There is still
no database, no authentication, no persistence, and nothing is deployed or
published to a registry. Verification here means "the documentation matches the
code", not "the system is hardened".

## 6. DRAFT - REWRITE IN MY OWN WORDS — Open Questions

1. **Should any of this run in CI?** A check that the OpenAPI `description` has not
   gone stale is cheap and would have caught the "Module 1 skeleton" string
   immediately. A check that every documented status code is reachable is much
   harder and might itself be vacuous.
2. ~~**Which `docs/` tree is canonical?**~~ **Resolved.** The top-level `docs/*.md`
   files are deliberate pointers, not stale duplicates: the brief names two
   locations, so the full documents live in `docs/midcourse/` and each is
   summarised at the top level. `docs/README.md` states this. An audit that had
   stopped at "these look like superseded stubs" would have recommended deleting
   a deliverable — a reminder that step 1 of the audit is reading the index
   before judging the tree.
3. **Is CI actually green?** The README states the 3.11 pins are "both verified
   green". The pins are real and confirmed. The green status has not been observed
   from this machine — `gh` is not installed. **[VERIFY]** against the Actions tab.
4. ~~**What is the image size?**~~ **Resolved.** Measured locally:
   `docker images` reports **293MB**, `docker image inspect .Size` reports
   **68,732,880 bytes**. The two disagree because the build produces an
   attestation manifest list; both are recorded rather than choosing one.
5. **Should the `.dockerignore` assertion be repaired or removed?** Still open,
   and now sharper. Both assertions in `docker-verify.yml` are
   non-discriminating on a runner: a fresh checkout has no `__pycache__` and none
   of the other checked paths are ever copied into the runtime stage, so both
   pass regardless of what `.dockerignore` contains. The underlying defect they
   were meant to catch was real and was found by building locally instead.
6. **Does `describe_value` truncation need fixing rather than documenting?** The
   docstring was narrowed to match the code. The alternative — truncating lists too
   — changes stored activity values and would need its own decision.
7. **Where does this note live?** `docs/decisions/` was created for it. The
   existing decision record is `docs/midcourse/mini-adr.md`. Two homes for
   decisions is one too many.

---

*I would do this differently by...*
