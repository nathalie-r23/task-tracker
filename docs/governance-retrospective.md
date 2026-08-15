# Governance Retrospective — AI-Assisted Coding

A record of what was shared with AI coding tools during this course, what was
received back, and the personal rules drawn from both.

**Scope limit, stated first:** the evidence below covers **one tool and one
session** — a Claude Code session on 2026-08-15 working on branch `ci-setup`.
Copilot, Codex and Cursor were also used during this course and are **not
audited here**. Rows marked *(unaudited)* need the same treatment.

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
| Backend models and validators | 2 | `app/models.py` — incl. `TaskUpdate.validate_title` and `validate_description` at :128-144, added this session | **Unsigned** — see §2.1 |
| Frontend board and drag-and-drop logic | 3 | `frontend/index.html` (2160 lines) | **Unsigned** |
| CI workflow | 4 | `.github/workflows/ci.yml`, `docker-verify.yml` | **Unsigned** |
| Dockerfile | 4 | `Dockerfile`, `.dockerignore` | **Unsigned** |
| Security findings and plans | 5 | `docs/security-review.md` | **Unsigned** |

### 2.1 Why this column is unsigned

This is a personal attestation and cannot be delegated to the tool that wrote
the code. It is left blank deliberately rather than filled in.

A line-by-line walkthrough of the highest-risk item — the validators at
`app/models.py:128-144` — was produced during this course and identified the
specific things a "yes" would require defending:

- Why `@field_validator` must sit above `@classmethod`, and what breaks if not.
- Why the validator does **not** run when a field is omitted from the payload —
  the undocumented Pydantic behaviour that the entire partial-update mechanism
  depends on.
- Why `title` raises on `null` while `description` converts it to `""`.
- Why this code raises `ValueError` rather than `HTTPException`, unlike
  `app/business_rules.py:40`.
- What the `exclude_unset=True` call at `app/storage.py:185` contributes — the
  other half of the mechanism, in a different file.

**To complete:** answer yes or no per row. A "no" is a more useful retrospective
entry than an unexamined "yes."

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

**Still to confirm:** whether any equivalent incident occurred in Copilot, Codex
or Cursor. Those sessions are unaudited, and the rule is only as good as its
coverage.

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

- **Three of four tools.** Copilot, Codex and Cursor received code and context
  during this course and have no equivalent record. Any incident in those
  sessions is undocumented.
- **The line-by-line attestation** in §2 is unsigned.
- **Modules 2 and 3** are covered only by the summary rows in §1; the detailed
  incident record in §1.1 is from a single Module 4/5 session.
