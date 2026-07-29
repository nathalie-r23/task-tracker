from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, computed_field, field_validator


class TaskStatus(str, Enum):
    TODO = "ToDo"
    IN_PROGRESS = "InProgress"
    DONE = "Done"


class TaskPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


def _validate_title(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("title must not be blank")
    if len(stripped) > 200:
        raise ValueError("title must be at most 200 characters")
    return stripped


def today_utc() -> date:
    """Today's calendar date in UTC.

    Overdue is judged against UTC because created_at/updated_at are UTC too;
    using the server's local date would make the rule depend on where the
    process happens to run.
    """
    return datetime.now(timezone.utc).date()


def compute_is_overdue(due_date: Optional[date], status: TaskStatus) -> bool:
    """A task is overdue when its due date has already passed and it is not Done.

    Deliberate choices (see docs/midcourse/mini-adr.md):
    - No due date -> never overdue.
    - Due *today* is not overdue; you still have the day to finish it.
    - Done tasks are never overdue, even if completed late. The board uses
      "overdue" to mean "needs attention now", and finished work does not.
    """
    if due_date is None:
        return False
    if status == TaskStatus.DONE:
        return False
    return due_date < today_utc()


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: Optional[str] = ""
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee: Optional[str] = None
    due_date: Optional[date] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _validate_title(value)


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee: Optional[str] = None
    due_date: Optional[date] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return _validate_title(value)


class TaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee: Optional[str]
    due_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_overdue(self) -> bool:
        """Derived on read, never stored — a stored flag would go stale at midnight."""
        return compute_is_overdue(self.due_date, self.status)
