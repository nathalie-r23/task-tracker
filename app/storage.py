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
# Keyed by task id, append-ordered (oldest first). Purged when the task goes.
_comments: dict[str, list[CommentResponse]] = {}
# One flat append-only log, oldest first, NOT keyed by task: entries outlive the
# tasks they describe, so there is no per-task bucket to put a deletion in.
# Per-task reads filter it. O(n) per lookup, which for an in-memory learning
# project is cheaper than keeping an index correct.
_activity: list[ActivityEntry] = []

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
    task_title: str,
    kind: ActivityKind,
    field: Optional[str] = None,
    from_value: Optional[str] = None,
    to_value: Optional[str] = None,
) -> ActivityEntry:
    entry = ActivityEntry(
        id=str(uuid4()),
        task_id=task_id,
        task_title=task_title,
        kind=kind,
        field=field,
        from_value=from_value,
        to_value=to_value,
        at=datetime.now(timezone.utc),
    )
    _activity.append(entry)
    return entry


def _with_comment_count(task: TaskResponse) -> TaskResponse:
    """Stamp the live comment count on the way out.

    Derived at read rather than stored, so it cannot drift from the comment
    store — the same reasoning as `is_overdue`, but done here because the model
    has no way to reach storage. See docs/midcourse/mini-adr.md Decision 13.
    """
    return task.model_copy(update={"comment_count": len(_comments.get(task.id, []))})


def add_task(payload: TaskCreate) -> TaskResponse:
    """Store a new task and record its `created` activity entry.

    Args:
        payload: Validated fields from the request body. A `None` description
            is normalised to `""`.

    Returns:
        The stored task with a server-assigned UUID `id`, `created_at` and
        `updated_at` set to the same UTC instant, and `comment_count` of 0.
    """
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
    _record_activity(task_id, task.title, ActivityKind.CREATED)
    return _with_comment_count(task)


def get_all_tasks(status=None, priority=None, overdue=None, tag=None, q=None) -> list[TaskResponse]:
    """Return stored tasks, narrowed by any combination of filters.

    Every supplied filter is applied, so they combine with AND. A filter left
    as `None` is skipped entirely.

    Args:
        status: `TaskStatus` to match exactly, or None.
        priority: `TaskPriority` to match exactly, or None.
        overdue: Bool matched against each task's computed `is_overdue`, or
            None for no overdue filtering.
        tag: Tag to match case-insensitively against any one of a task's tags,
            or None. Surrounding whitespace is trimmed.
        q: Literal substring searched case-insensitively in title and
            description only — never a regex, so `.*` matches those two
            characters. Whitespace-only means "no search", not "match
            nothing".

    Returns:
        Matching tasks in insertion order, each stamped with its live
        `comment_count`.
    """
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
    """Look up one task.

    Args:
        task_id: The task's UUID string.

    Returns:
        The task with its live `comment_count`, or None when the id is
        unknown, so the route can answer 404.
    """
    task = _tasks.get(task_id)
    return None if task is None else _with_comment_count(task)


def update_task(task_id: str, payload: TaskUpdate) -> Optional[TaskResponse]:
    """Apply a partial update and log one activity entry per changed field.

    Fields absent from the request body are left untouched — `exclude_unset`
    distinguishes "not sent" from "sent as null".

    Two timing details that are easy to get wrong:

    - A body with no fields at all returns the task unchanged and does **not**
      touch `updated_at`.
    - A body that re-sends a field's current value **does** bump `updated_at`,
      because a field was set, but records **no** activity entry, because
      nothing actually moved.

    Args:
        task_id: The task's UUID string.
        payload: The subset of fields to change.

    Returns:
        The updated task with its live `comment_count`, or None when the id is
        unknown, so the route can answer 404.
    """
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
                updated_task.title,
                ActivityKind.UPDATED,
                field=name,
                from_value=describe_value(before),
                to_value=describe_value(after),
            )

    return _with_comment_count(updated_task)


def delete_task(task_id: str) -> bool:
    """Remove a task and its comments, keeping its activity.

    Records a `deleted` entry before returning, so the board-wide feed can
    still report what happened to a task that no longer exists.

    Args:
        task_id: The task's UUID string.

    Returns:
        True when a task was removed, False when the id was unknown — the
        route turns False into a 404.
    """
    existing = _tasks.get(task_id)
    if existing is None:
        return False

    del _tasks[task_id]
    # Comments go: they are only reachable through /tasks/{id}/comments, which
    # 404s once the task does not exist, so keeping them would leak records
    # nothing can read. Activity stays — GET /activity can still read it, and a
    # history that silently forgets deletions is not a history.
    _comments.pop(task_id, None)
    _record_activity(task_id, existing.title, ActivityKind.DELETED)
    return True


def add_comment(task_id: str, payload: CommentCreate) -> Optional[CommentResponse]:
    """Append a comment. Returns None when the task does not exist, so the route
    can answer 404 rather than inventing a thread.

    Records a `commented` activity entry carrying the author in `from_value`
    and a truncated preview of the body in `to_value`.

    Args:
        task_id: The task's UUID string.
        payload: Validated comment fields.

    Returns:
        The stored comment with a server-assigned `id` and `created_at`, or
        None when the task id is unknown.
    """
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
        _tasks[task_id].title,
        ActivityKind.COMMENTED,
        from_value=payload.author,
        to_value=describe_value(payload.body),
    )
    # Deliberately does not touch the task's updated_at: commenting on a task
    # is not editing it.
    return comment


def get_comments(task_id: str) -> Optional[list[CommentResponse]]:
    """Oldest first — a discussion reads forwards.

    Args:
        task_id: The task's UUID string.

    Returns:
        A copy of the task's comments, or None when the id is unknown. An
        existing task with no comments returns an empty list, which is a
        different answer from None.
    """
    if task_id not in _tasks:
        return None
    return list(_comments.get(task_id, []))


def get_activity(task_id: str) -> Optional[list[ActivityEntry]]:
    """One task's history, newest first — a changelog reads backwards.

    Returns None for an unknown task so the route can 404. That includes a task
    that has been deleted: the task resource is gone, so its sub-resource is
    gone with it. Its entries, including the deletion itself, remain readable on
    the board-wide feed.

    Args:
        task_id: The task's UUID string.

    Returns:
        The task's entries newest first, or None when the task does not
        currently exist.
    """
    if task_id not in _tasks:
        return None
    return [entry for entry in reversed(_activity) if entry.task_id == task_id]


def get_all_activity(kind=None, task_id=None, limit: int = 50) -> list[ActivityEntry]:
    """The board-wide feed, newest first.

    Unlike the per-task view this does not 404 on an unknown id — it is a log,
    not a sub-resource, and asking it about a task that no longer exists is the
    normal way to find out what happened to it.

    Args:
        kind: `ActivityKind` to match exactly, or None for every kind.
        task_id: Restrict to one task, or None for the whole board. An unknown
            or deleted id yields `[]`, never an error.
        limit: Maximum entries returned, applied after filtering. The route
            bounds this; the default here mirrors `DEFAULT_ACTIVITY_LIMIT`.

    Returns:
        Matching entries, newest first, truncated to `limit`.
    """
    entries = list(reversed(_activity))
    if kind is not None:
        entries = [e for e in entries if e.kind == kind]
    if task_id is not None:
        entries = [e for e in entries if e.task_id == task_id]
    return entries[:limit]


def _reset() -> None:
    _tasks.clear()
    _comments.clear()
    _activity.clear()


MAX_ACTIVITY_LIMIT = 200
DEFAULT_ACTIVITY_LIMIT = 50
