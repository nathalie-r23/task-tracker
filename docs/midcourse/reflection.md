# Reflection

I used Claude Code throughout, in three modes that were not equally useful.
Reconnaissance: before touching anything, mapping the models, routes, storage
layer and test conventions, with instructions not to propose changes.
Constrained generation: prompts stating the types, the validation rules, the
boundary semantics and the files it was allowed to touch. Execution: running
`pytest` after every step and driving the live board in a browser to read values
back out of the DOM.

The clearest win came from the reconnaissance pass. `storage.update_task`
rebuilt a task with `TaskResponse(**existing.model_dump())`, and `TaskResponse`
is declared `extra="forbid"`. Because I had that in front of me before I
designed `is_overdue`, I could see that adding a Pydantic computed field would
make `model_dump()` emit a key the constructor refuses — breaking *every*
`PATCH`, not just the new feature. Had I gone straight to the feature, I would
have been staring at a wall of unrelated failing tests trying to work out what I
broke.

The slowdown was self-inflicted and instructive. I asked for a script to run the
Break Tests — patch a rule, run the guarding test, restore the file. The first
version had no `try/finally`, and when a subprocess call failed on a bad
interpreter path it exited with `models.py` still holding the broken comparison.
The generated code was fine for the happy path and dangerous for the failure
path, which is the specific weakness of code that edits source in place. The
rewrite restores in a `finally` block and refuses to start unless every target
file is already clean. A duller detour went to environment plumbing: a static
server that ignored the port it was handed, and a browser tool sandboxed away
from localhost.

Review changed the outcome most on semantics. Left alone, the assistant produced
`due_date <= today` with no status check — so a task due today was instantly red,
and work finished late stayed red permanently. Both are defensible as code and
wrong as product. Tags were first lower-cased, handing back `api` to someone who
typed `API`.

The sharpest instance came last, and it was a review of the tests rather than the
code. I asked which tests would still pass if the rule they claimed to cover were
broken. It found one asserting a timestamp had *not* changed — true
automatically, because the clock does not advance during a sub-millisecond
request. That test could not fail. Chasing it surfaced a pre-existing flaky test
with the same cause and the opposite symptom. Measuring instead of re-running
showed 20,000 calls to `datetime.now()` returning two distinct values: an 8ms
clock.

The habit worth keeping is stating the contract first and verifying it after —
Break Tests to prove a test can fail, intercepting `fetch` to prove a refactor
changed nothing on the wire, and measuring a flake instead of retrying it.
