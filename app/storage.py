from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.models import (
    ActivityEntry,
    ActivityKind,
    CommentCreate,
    CommentResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    describe_value,
)

_tasks: dict[str, TaskResponse] = {}
# Both keyed by task id, both append-ordered (oldest first).
_comments: dict[str, list[CommentResponse]] = {}
_activity: dict[str, list[ActivityEntry]] = {}

# Fields whose changes are worth a line in the activity log. `updated_at` is
# excluded: it changes on every write and would double the log saying nothing.
TRACKED_FIELDS: tuple[str, ...] = (
    "title",
    "description",
    "status",
    "priority",
    "assignee",
    "due_date",
    "tags",
)


def _record_activity(
    task_id: str,
    kind: ActivityKind,
    field: Optional[str] = None,
    from_value: Optional[str] = None,
    to_value: Optional[str] = None,
) -> ActivityEntry:
    entry = ActivityEntry(
        id=str(uuid4()),
        task_id=task_id,
        kind=kind,
        field=field,
        from_value=from_value,
        to_value=to_value,
        at=datetime.now(timezone.utc),
    )
    _activity.setdefault(task_id, []).append(entry)
    return entry


def _with_comment_count(task: TaskResponse) -> TaskResponse:
    """Stamp the live comment count on the way out.

    Derived at read rather than stored, so it cannot drift from the comment
    store — the same reasoning as `is_overdue`, but done here because the model
    has no way to reach storage. See docs/midcourse/mini-adr.md Decision 13.
    """
    return task.model_copy(update={"comment_count": len(_comments.get(task.id, []))})


def add_task(payload: TaskCreate) -> TaskResponse:
    now = datetime.now(timezone.utc)
    task_id = str(uuid4())
    task = TaskResponse(
        id=task_id,
        title=payload.title,
        description=payload.description or "",
        status=payload.status,
        priority=payload.priority,
        assignee=payload.assignee,
        due_date=payload.due_date,
        tags=payload.tags,
        created_at=now,
        updated_at=now,
    )
    _tasks[task_id] = task
    _record_activity(task_id, ActivityKind.CREATED, to_value=describe_value(task.title))
    return _with_comment_count(task)


def get_all_tasks(status=None, priority=None, overdue=None, tag=None, q=None) -> list[TaskResponse]:
    tasks = list(_tasks.values())
    if status is not None:
        tasks = [t for t in tasks if t.status == status]
    if priority is not None:
        tasks = [t for t in tasks if t.priority == priority]
    if overdue is not None:
        tasks = [t for t in tasks if t.is_overdue == overdue]
    if tag is not None:
        # Case-insensitive so ?tag=bug finds a task tagged "Bug".
        wanted = tag.strip().casefold()
        tasks = [t for t in tasks if any(existing.casefold() == wanted for existing in t.tags)]
    if q is not None:
        # Literal substring, not a pattern: ?q=.* looks for the characters ".*".
        # A blank or whitespace-only term means "no search", not "match nothing".
        needle = q.strip().casefold()
        if needle:
            tasks = [
                t for t in tasks
                if needle in t.title.casefold() or needle in t.description.casefold()
            ]
    return [_with_comment_count(t) for t in tasks]


def get_task_by_id(task_id: str) -> Optional[TaskResponse]:
    task = _tasks.get(task_id)
    return None if task is None else _with_comment_count(task)


def update_task(task_id: str, payload: TaskUpdate) -> Optional[TaskResponse]:
    existing = _tasks.get(task_id)
    if existing is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return _with_comment_count(existing)

    # Only real fields — model_dump() would also emit computed ones such as
    # is_overdue, which TaskResponse(extra="forbid") then rejects on rebuild.
    updated_data = {name: getattr(existing, name) for name in TaskResponse.model_fields}
    updated_data.update(updates)
    updated_data["updated_at"] = datetime.now(timezone.utc)

    updated_task = TaskResponse(**updated_data)
    _tasks[task_id] = updated_task

    # One entry per field that actually moved. A PATCH re-sending a field's
    # current value is in `updates` but is not a change, so it logs nothing.
    for name in TRACKED_FIELDS:
        before = getattr(existing, name)
        after = getattr(updated_task, name)
        if before != after:
            _record_activity(
                task_id,
                ActivityKind.UPDATED,
                field=name,
                from_value=describe_value(before),
                to_value=describe_value(after),
            )

    return _with_comment_count(updated_task)


def delete_task(task_id: str) -> bool:
    if task_id in _tasks:
        del _tasks[task_id]
        # Comments and activity are only reachable through this task's routes,
        # so keeping them would leak records nothing can ever read.
        _comments.pop(task_id, None)
        _activity.pop(task_id, None)
        return True
    return False


def add_comment(task_id: str, payload: CommentCreate) -> Optional[CommentResponse]:
    """Append a comment. Returns None when the task does not exist, so the route
    can answer 404 rather than inventing a thread."""
    if task_id not in _tasks:
        return None

    comment = CommentResponse(
        id=str(uuid4()),
        task_id=task_id,
        author=payload.author,
        body=payload.body,
        created_at=datetime.now(timezone.utc),
    )
    _comments.setdefault(task_id, []).append(comment)
    _record_activity(
        task_id,
        ActivityKind.COMMENTED,
        from_value=payload.author,
        to_value=describe_value(payload.body),
    )
    # Deliberately does not touch the task's updated_at: commenting on a task
    # is not editing it.
    return comment


def get_comments(task_id: str) -> Optional[list[CommentResponse]]:
    """Oldest first — a discussion reads forwards."""
    if task_id not in _tasks:
        return None
    return list(_comments.get(task_id, []))


def get_activity(task_id: str) -> Optional[list[ActivityEntry]]:
    """Newest first — a changelog reads backwards."""
    if task_id not in _tasks:
        return None
    return list(reversed(_activity.get(task_id, [])))


def _reset() -> None:
    _tasks.clear()
    _comments.clear()
    _activity.clear()
