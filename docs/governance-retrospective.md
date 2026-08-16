# Governance Retrospective — AI-Assisted Coding

A record of what was shared with AI coding tools during this course, what was
received back, and the personal rules drawn from both.

**Scope limit, stated first:** the three incidents in §1.1 are **observed** — they
come from a Claude Code session on 2026-08-15 where the transcript was available.
Everything else is **recall**. Copilot and Codex are recorded from memory with no
session history reviewed; Cursor was not used on this project. Recall and
transcript are different grades of evidence and are kept distinct throughout.

---

## 1. What I shared with AI

Risk rubric:

- **Low** — public code, course toy project code, no sensitive data, no
  proprietary logic.
- **Medium** — private but non-sensitive code, internal implementation details,
  or non-public repo context with no secrets and no PII.
- **High** — credentials, tokens, secrets, production config, real customer/user
  data, regulated data, or code I am not authorized to share.

| Item shared | Module | Risk | Reason | Safer future version |
|---|---|---|---|---|
| Task Tracker source code | 2–5 | **Low** | Course project: no proprietary logic, no customer data, no regulated data. Already pushed to GitHub | Scope reads to the files a task needs rather than granting the whole tree, so the habit transfers to a work repo |
| Test output and stack traces | 2–4 | **Low** here · **Medium as a habit** | What was shared — pytest summaries and one Pydantic `ValidationError` — held only local paths and field names. But stack traces are the classic accidental-leak vector: on a project with a database or API client they routinely carry connection strings or tokens | Paste the failing assertion and the exception message. If a full trace is needed, scan the frames for values first |
| Frontend code | 3 | **Low** | `frontend/index.html` has a hardcoded `http://localhost:8000` and no keys, analytics IDs or third-party tokens | Fine as-is. On a real frontend, strip API keys and endpoint URLs — those are the assets that live in client code |
| Dockerfile and CI YAML | 4 | **Low** here · **Medium as a habit** | Verified clean: no `ENV`/`ARG` carrying credentials, both workflows set `permissions: contents: read`, no `secrets.*` references. But CI config is where real projects keep secret names, registry credentials and deploy targets | Grep for `secrets.`, `env:` and registry URLs before pasting. Share job structure, redact the rest |
| Real external data used by mistake | — | **See §1.1** | Three incidents observed in-session; none reached the High tier, but all three are habits that would | See §1.1 |
| Shared with **GitHub Copilot** — feature code in the editor | 2–3 | **Low** | Task Tracker source only: models, validators, tests and board code, none of it proprietary or carrying data. One incident of a *wrong suggestion* rather than a disclosure — it proposed `<=` for the overdue comparison, which a test caught. No credentials or personal data recalled | Same rule as the rest: keep credential files out of editor context, and treat a plausible completion as unverified until a test runs |
| Shared with **Codex App** — repo diff and context for review | 5 | **Low** | The `ci-setup` diff and repository context for the Module 5 security review. No secrets; it produced findings, which were graded rather than accepted. Its dependency advisories for `python-dotenv` and `pytest` were checked and both affected versions below our pins | Fine as-is for a public course repo. On a private repo, note that the diff and its context leave the machine |
| Shared with **Cursor** — feature code during Module 3 | 3 | **Low** | Task Tracker source only. Evidenced rather than recalled: commit `8c547b4` ("module 3 - before refactor, functionality ok") carries `Co-authored-by: Cursor <cursoragent@cursor.com>`, and Cursor appears in the repository's Contributors list. No credentials or personal data recalled, and no incident recalled | Same rule as the other editors: keep credential files out of the workspace context, and treat a plausible multi-file edit as unverified until the suite runs |

**The three rows above are mostly recall, not transcript evidence**, and the
difference matters: "none recalled" is a weaker claim than "none found." No
session logs were reviewed for any of the three. All retain chat history, so
scrolling would upgrade these rows — that check has not been done.

**One correction worth recording, because it shows how weak recall is.** The
Cursor row first read "not used on this project" — written from memory and
confirmed twice in conversation. The repository disagreed: commit `8c547b4`
carries a `Co-authored-by: Cursor <cursoragent@cursor.com>` trailer, and Cursor
is listed among this repository's three Contributors on GitHub. A tool used for
part of a module was forgotten within weeks, and the error was caught only
because the Contributors panel happened to be visible in a screenshot. Anything
in this document not backed by a commit, a transcript or a command should be read
with that in mind.

**The one question that could reach High:** did any of them ever receive a
`.env`, a credential, or a stack trace from a project that was not this toy?

### 1.1 Incidents observed in this session

These are **observed events**, not hypotheticals. Each is verifiable in the
session history. None involved a credential, token, or production config, so
none reaches **High** under the rubric — but each is the low-stakes version of
something that would.

| Incident | Risk | What actually happened | Why it matters anyway |
|---|---|---|---|
| `.env` was opened by the AI during the security audit | **Low** | The file holds `PORT=8000` and `APP_ENV=development`. Values were redacted before printing, so no value entered the transcript | Letting a tool read `.env` is the habit that leaks a real key on a different project. The safe outcome here was luck of contents, not of process |
| A personal email address entered the transcript | **Medium** | `nathalie.riachi@gmail.com` appeared via `git show` / `git log` author fields, alongside a different account email on the session | PII, disclosed as a side effect of a command run for another purpose. `git log --format="%h %s"` omits author fields |
| A copyrighted course slide was shared as an image | **Medium** | The Module 4 deliverables slide, carrying "© All rights reserved, American University of Beirut" and showing an identifiable person in a video thumbnail | Third-party copyrighted material and a person's likeness, neither mine to redistribute. The content needed was eight deliverable names — retyping them as text carries neither risk |

**The pattern worth keeping:** every row in §1 is Low or Medium *because this is
a toy project with no secrets*, not because the sharing was careful. Rows 2 and
4 would be Medium-to-High verbatim on a work repository. The useful question is
not "what did I share" but "which of these habits would still be safe if the
repo weren't a toy."

---

## 2. What I received from AI

| Generated thing | Module | Where it lives now | Do I understand it line by line? |
|---|---|---|---|
| Backend models and validators | 2 | `app/models.py` — incl. `TaskUpdate.validate_title` and `validate_description` at :128-144 | **Partial** — I can explain what the validators do and why `title` rejects null while `description` clears to `""`, but I have not worked through the Pydantic behaviour they depend on myself |
| Frontend board and drag-and-drop logic | 3 | `frontend/index.html` (2160 lines) | **No** — most of the file has never been read, by me or by any review in this repo |
| CI workflow | 4 | `.github/workflows/ci.yml`, `docker-verify.yml` | **Partial** — I accepted a step that later turned out to be incapable of failing, which is the clearest evidence that my understanding was incomplete when I approved it |
| Dockerfile | 4 | `Dockerfile`, `.dockerignore` | **Yes** — 49 commented lines, and I have now built and run the image and checked its user, contents and health endpoint |
| Security findings and plans | 5 | `docs/security-review.md` | **Yes** — I graded all seven findings and rejected four, which required understanding each well enough to disagree with it |

Add a half-sentence to anything that is not a clean Yes. A **No** is a
legitimate entry and a more useful retrospective record than an unexamined Yes.

### 2.1 What those answers claim

Two **Yes**, two **Partial**, one **No**. The mix is the point: a column of five
Yeses would be the least believable version of this table, and the two weakest
rows are backed by specific evidence of incomplete understanding rather than by
modesty.

A line-by-line walkthrough of the highest-risk item — the validators at
`app/models.py:128-144` — was produced during this course and identified the
specific things a "Yes" there would require defending, which is why that row is
**Partial**:

- Why `@field_validator` must sit above `@classmethod`, and what breaks if not.
- Why the validator does **not** run when a field is omitted from the payload —
  the undocumented Pydantic behaviour that the entire partial-update mechanism
  depends on.
- Why `title` raises on `null` while `description` converts it to `""`.
- Why this code raises `ValueError` rather than `HTTPException`, unlike
  `app/business_rules.py:40`.
- What the `exclude_unset=True` call at `app/storage.py:185` contributes — the
  other half of the mechanism, in a different file.

The frontend row is a flat **No** for the same reason in reverse: no review in
this repository has read more than about 400 of its 2160 lines, so there is no
basis for claiming otherwise.

---

## 3. Three personal rules

### Rule 1 — What I will never paste

> I will not let an AI tool read `.env`, credential files, or any file I have
> not opened myself first. When a tool needs to know about configuration, I tell
> it the variable names and say the values are non-secret — I do not grant the
> read. Before running a git command in an AI session I check whether its output
> carries author emails, and use `--format` to strip them when it does. I do not
> share course slides, screenshots of other people's material, or images
> containing identifiable people; I retype the content I actually need.

**Evidence:** §1.1 — three observed incidents. The `.env` read, the author email
disclosed via `git show`, and the AUB-copyrighted slide with a visible person.

**How a teammate could tell it was violated:** a transcript containing the
contents of a credential file, an email address in command output, or a
screenshot of third-party material.

**Coverage limit:** no equivalent incident is recalled from Copilot or Codex, but
neither set of session logs was reviewed, so this is "none recalled" rather than
"none found." The rule is only as good as its coverage, and its coverage is one
tool's transcript plus memory for the rest.

### Rule 2 — What I will always verify before accepting

> Before accepting an AI claim about behaviour — a status code, a limit, a
> validation outcome — I run the behaviour and record the command. I do not
> accept a claim confirmed only by reading the code. If I cannot run the check,
> I write `[VERIFY]` in the document and name what access would settle it, rather
> than asserting it and moving on.

**Evidence:** `docs/checklists/doc-claim-audit.md` step 4 ("Probe, don't read")
and its rule that evidence must be "the command, not a summary of it."
`docs/module4/annotated-review-log.md` pairs every Useful finding with the
command that confirmed it. `docs/module4/docker-security-log.md` is the
`[VERIFY]` half in practice — it states "claims pending evidence" rather than
asserting non-root, because the Docker engine never started.

**Why the clause matters:** during this course, five documentation claims were
disproved by executing them, including one that produced an HTTP 500. All five
had survived at least one careful read.

### Rule 3 — How I will record AI contributions

> Every commit containing AI-generated code carries a `Co-Authored-By` trailer.
> Any AI review output that informs a decision is written to a file in `docs/`
> with each finding graded and its evidence cited — **before the conversation
> ends, not after.** I record rejected AI output too, not only what I accepted.

**Evidence:** seven commits on `ci-setup` carry `Co-Authored-By: Claude Opus 5`.
`docs/security-review.md` grades seven AI findings Valid / False Positive /
Noise with file:line evidence. `docs/module4/annotated-review-log.md` records the
one **Wrong** finding — a confident, line-count-backed claim that the top-level
`docs/*.md` files were superseded stubs, which would have deleted a graded
deliverable had it been acted on.

**Why "before the conversation ends":** the security review, the review log and
this retrospective all nearly died in a chat transcript. They exist as files only
because they were written out at the end of the session that produced them.

---

## 4. What this retrospective does not cover

- **Two tools are covered by recall, not records.** The Copilot and Codex rows in
  §1 describe what was shared from memory; no session history was reviewed for
  either. Both retain chat logs, so those rows could be upgraded from "none
  recalled" to "none found" — that has not been done. Cursor was not used on this
  project, so there is nothing to audit there.
- **Only §1.1 rests on observed evidence.** Those three incidents come from a
  single Claude Code session where the transcript was available. Everything in
  §1 covering Modules 2–3 is summary-level.
- **The attestation in §2 is self-assessed**, which is what an attestation is —
  but it is not the same as being tested. Only the backend row has a written
  walkthrough behind its answer.
