# Reflection

I used Claude Code throughout, in three distinct modes, and they were not equally
useful. The first was reconnaissance: before touching anything I had it map the
models, routes, storage layer and test conventions, with instructions not to
propose changes. The second was constrained generation — prompts that stated the
types, the validation rules, the boundary semantics and the files it was allowed
to touch. The third was execution: running `pytest` after every step and driving
the live board in a browser to read values back out of the DOM.

The clearest win came from the reconnaissance pass. `storage.update_task`
rebuilds a task with `TaskResponse(**existing.model_dump())`, and `TaskResponse`
is declared `extra="forbid"`. Because I had that in front of me before I designed
`is_overdue`, I could see that adding a Pydantic computed field would make
`model_dump()` emit a key the constructor refuses — breaking *every* `PATCH`, not
just the new feature. I changed the rebuild to walk `TaskResponse.model_fields`
first. Had I gone straight to the feature, I would have been staring at a wall of
unrelated failing tests trying to work out what I broke.

The slowdown was self-inflicted and instructive. I asked for a script to run the
Break Tests — patch a rule, run the guarding test, restore the file. The first
version had no `try/finally`, and when a subprocess call failed on a bad
interpreter path it exited with `models.py` still holding the broken comparison.
The generated code was fine for the happy path and dangerous for the failure
path, which is the specific weakness of code that edits source in place. I
rewrote it to restore in a `finally` block and to assert the file was clean
before starting. A second, duller detour went to environment plumbing: a static
server that ignored the port it was handed, and a browser tool sandboxed away
from localhost. Neither taught me anything about the feature.

Where my review changed the outcome most was semantics. Left alone, the
assistant produced `due_date <= today` with no status check — so a task due today
was instantly red, and work finished late stayed red permanently. Both are
defensible as code and wrong as product. I forced the boundary cases to be
enumerated before any code was written, which turned a silent default into an
argument I could win. The same thing happened with tags: the first version
lower-cased them, handing back `api` to someone who typed `API`. Dedup should not
mean rewriting what a user typed.

The habit worth keeping is stating the contract first and verifying it after —
Break Tests to prove a test can fail, and intercepting `fetch` to prove a
refactor changed nothing on the wire.
