from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.models import TaskCreate, TaskResponse, TaskUpdate

_tasks: dict[str, TaskResponse] = {}


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
    return task


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
    return tasks


def get_task_by_id(task_id: str) -> Optional[TaskResponse]:
    return _tasks.get(task_id)

def update_task(task_id: str, payload: TaskUpdate) -> Optional[TaskResponse]:
    existing = _tasks.get(task_id)
    if existing is None:
        return None

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return existing

    # Only real fields — model_dump() would also emit computed ones such as
    # is_overdue, which TaskResponse(extra="forbid") then rejects on rebuild.
    updated_data = {name: getattr(existing, name) for name in TaskResponse.model_fields}
    updated_data.update(updates)
    updated_data["updated_at"] = datetime.now(timezone.utc)

    updated_task = TaskResponse(**updated_data)
    _tasks[task_id] = updated_task
    return updated_task


def delete_task(task_id: str) -> bool:
    if task_id in _tasks:
        del _tasks[task_id]
        return True
    return False


def _reset() -> None:
    _tasks.clear()
