"""Application entry point.

Creates and configures the FastAPI application instance for the
Module 1 Task Tracker API. Only the health endpoint is wired up at
this stage — no CRUD, storage, or business logic yet.
"""

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app import storage
from app.api.routes import health
from app.business_rules import validate_status_transition
from app.core.config import settings
from app.models import (
    ActivityEntry,
    ActivityKind,
    CommentCreate,
    CommentResponse,
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="Task Tracker API",
        description="Module 1 learning project — REST API skeleton.",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        # "null" covers opening frontend/index.html straight from disk (file://).
        # The regex covers any local static-server port, so the board keeps working
        # whether it is served on 5500, 5173, or whatever a dev tool picks.
        allow_origins=["null"],
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    # Register routers. Each router owns a slice of the API surface.
    app.include_router(health.router)

    return app


# The ASGI app object Uvicorn looks for: `app.main:app`.
app = create_app()


@app.get("/tasks", response_model=list[TaskResponse], tags=["tasks"])
def list_tasks(
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    overdue: bool | None = None,
    tag: str | None = None,
    q: str | None = None,
) -> list[TaskResponse]:
    """List tasks, optionally narrowed by status, priority, overdue state, tag and/or text.

    `overdue` is tri-state: omitted returns everything, `true` returns only
    overdue tasks, `false` returns only tasks that are not overdue. `tag`
    matches case-insensitively. `q` is a case-insensitive literal substring
    matched against title or description; blank means no search. All filters
    combine with AND.
    """
    return storage.get_all_tasks(
        status=status, priority=priority, overdue=overdue, tag=tag, q=q
    )


@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["tasks"])
def create_task(payload: TaskCreate) -> TaskResponse:
    return storage.add_task(payload)


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def get_task(task_id: str) -> TaskResponse:
    task = storage.get_task_by_id(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    return task


@app.patch("/tasks/{task_id}", response_model=TaskResponse, tags=["tasks"])
def update_task(task_id: str, payload: TaskUpdate) -> TaskResponse:
    if payload.status is not None:
        existing = storage.get_task_by_id(task_id)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
        validate_status_transition(existing.status, payload.status)

    task = storage.update_task(task_id, payload)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tasks"])
def delete_task(task_id: str) -> None:
    if not storage.delete_task(task_id):
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")


@app.post(
    "/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["comments"],
)
def create_comment(task_id: str, payload: CommentCreate) -> CommentResponse:
    """Append a comment to a task. Commenting does not change the task itself."""
    comment = storage.add_comment(task_id, payload)
    if comment is None:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    return comment


@app.get("/tasks/{task_id}/comments", response_model=list[CommentResponse], tags=["comments"])
def list_comments(task_id: str) -> list[CommentResponse]:
    """A task's comments, oldest first. Unknown task is 404, not an empty list —
    a mistyped id should not look like a task nobody has commented on."""
    comments = storage.get_comments(task_id)
    if comments is None:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    return comments


@app.get("/tasks/{task_id}/activity", response_model=list[ActivityEntry], tags=["activity"])
def list_activity(task_id: str) -> list[ActivityEntry]:
    """A task's history, newest first: one entry per changed field, plus
    creation and comments.

    `404` for an unknown task, including one that has been deleted — the task
    resource is gone, so its sub-resource is too. Its entries stay readable on
    `GET /activity`.
    """
    entries = storage.get_activity(task_id)
    if entries is None:
        raise HTTPException(status_code=404, detail=f"Task with id {task_id} not found")
    return entries


@app.get("/activity", response_model=list[ActivityEntry], tags=["activity"])
def list_all_activity(
    kind: ActivityKind | None = None,
    task_id: str | None = None,
    limit: int = Query(
        default=storage.DEFAULT_ACTIVITY_LIMIT, ge=1, le=storage.MAX_ACTIVITY_LIMIT
    ),
) -> list[ActivityEntry]:
    """Activity across every task, newest first.

    This is the only place a `deleted` entry can be read, and the only place a
    deleted task's history survives. Unlike the per-task route it never 404s:
    it is a log, not a sub-resource, so asking about an id that no longer exists
    is the normal way to find out what happened to it — it just returns `[]` if
    there is nothing.

    `limit` is capped rather than unbounded because the log only grows.
    """
    return storage.get_all_activity(kind=kind, task_id=task_id, limit=limit)