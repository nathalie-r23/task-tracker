from fastapi import HTTPException, status

from app.models import TaskStatus

VALID_TRANSITIONS: frozenset[tuple[TaskStatus, TaskStatus]] = frozenset({
    (TaskStatus.TODO, TaskStatus.IN_PROGRESS),
    (TaskStatus.IN_PROGRESS, TaskStatus.DONE),
    (TaskStatus.DONE, TaskStatus.IN_PROGRESS),
    (TaskStatus.TODO, TaskStatus.TODO),
    (TaskStatus.IN_PROGRESS, TaskStatus.IN_PROGRESS),
    (TaskStatus.DONE, TaskStatus.DONE),
})


def validate_status_transition(current: TaskStatus, new: TaskStatus) -> None:
    """Reject a status change that is not on the allow-list.

    A guard, not a transformer: it either returns quietly or raises. Called
    only from `PATCH /tasks/{task_id}`, and only when the request body carries
    a `status`. `POST /tasks` does not call it, so a task may be *created* in
    any status — the rule constrains movement, not the starting point.

    Same-status pairs are members of `VALID_TRANSITIONS`, so a no-op PATCH
    (for example `InProgress` to `InProgress`) is allowed.

    Args:
        current: The task's stored status.
        new: The status the caller is asking for.

    Returns:
        None when the transition is allowed.

    Raises:
        HTTPException: 422 when `(current, new)` is not in
            `VALID_TRANSITIONS`. The detail names both statuses and lists
            every allowed transition as sorted `From->To` strings.
    """
    if (current, new) not in VALID_TRANSITIONS:
        allowed = sorted({f"{f.value}->{t.value}" for f, t in VALID_TRANSITIONS})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status transition from {current.value} to {new.value}. Allowed transitions: {allowed}",
        )
