# Course Reflection — AI-Assisted Coding

## Which tool for which task shape

I used a different tool in each phase, and looking back the split tracks the kind
of work more than the quality of the tool. In Modules 2–3 I built features with
**GitHub Copilot** — continuous editor pairing, where the next few lines are
largely determined by the ones above them. Writing a validator that mirrors the
one above it, or a test that follows an established naming pattern, is exactly
that shape. Working on the overdue rule, it suggested the comparison as `<=`,
which would have marked tasks due *today* as overdue; a test caught it and I
changed it to `<` (`app/models.py:92`, and `test_due_today_is_not_overdue` in
`tests/test_tasks.py`). It saved me perhaps ten or fifteen minutes, but the edge
case was still mine to verify — which is the honest summary of that whole phase.
**Cursor** was also in that phase: commit `8c547b4` carries a Cursor co-author
trailer from Module 3. I had forgotten that entirely until the repository's
Contributors list contradicted me, which is its own small lesson about trusting
recall over records. Module 4 was Docker,
CI, docstrings and the README, and I used **Claude Code**: that phase was less
about writing than about running — building an image, hitting an endpoint,
checking what a container actually contains.
Module 5 was review, security and governance in **Codex App**, which is reading a
diff and forming a judgement about it without needing to execute anything.

The clearest thing I learned is that the useful split is not tool against tool,
it is **reasoning work against execution work**. Drafting a Dockerfile is
reasoning; any of the three could produce a plausible one. Verifying it is
execution. My Dockerfile looked correct for weeks and passed CI the whole time,
and the first time I actually built the image on my own machine one of five
checks failed: `.dockerignore` had been shipping ten bytecode directories into
the image, because a bare `__pycache__` pattern only matches top-level entries
and every cache in this repo sits under `app/`.

I also cannot claim the tool deserves the credit for review. Of seven security
findings I graded, only three were Valid — two were Noise and two were False
Positives. One of those was a pair of dependency advisories for `python-dotenv`
and `pytest`; I looked both up and each affected versions *below* the ones we
pin, so there was nothing to fix. The value came from grading every finding, not
from the findings being good.

## My single most important rule

**A claim about behaviour is not verified until I have run it and recorded the
command.**

Eight things went wrong this course, and this rule would have caught seven of
them: the API describing itself as a "Module 1 skeleton" while serving ten
routes, a docstring claiming truncation that did not apply to lists, a `PATCH`
returning 500 instead of 422, a README telling readers to remap a port and then
curl the old one, a guidance file forbidding the Docker work happening in its own
branch, the `.dockerignore` defect, and a CI assertion that could not fail. Every
one of them had survived at least one careful reading.

The eighth needed a different rule. An AI review used accurate line counts to
conclude that some documentation files were stale duplicates; they were
deliberate pointers, and acting on it would have deleted a graded deliverable.
Running something would not have helped there. That one needed *read the index
before judging the tree*, and I do not yet have a general defence against a
confident inference about intent.
