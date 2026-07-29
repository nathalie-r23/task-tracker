"""Application entry point.

Creates and configures the FastAPI application instance for the
Module 1 Task Tracker API. Only the health endpoint is wired up at
this stage — no CRUD, storage, or business logic yet.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app import storage
from app.api.routes import health
from app.business_rules import validate_status_transition
from app.core.config import settings
from app.models import TaskCreate, TaskPriority, TaskResponse, TaskStatus, TaskUpdate


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
) -> list[TaskResponse]:
    """List tasks, optionally narrowed by status, priority and/or overdue state.

    `overdue` is tri-state: omitted returns everything, `true` returns only
    overdue tasks, `false` returns only tasks that are not overdue.
    """
    return storage.get_all_tasks(status=status, priority=priority, overdue=overdue)


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