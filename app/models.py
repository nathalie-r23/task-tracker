from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


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


MAX_TAGS = 10
MAX_TAG_LENGTH = 24


def _validate_tags(values: list[str]) -> list[str]:
    """Trim, reject blanks/overlong tags, and drop case-insensitive duplicates.

    Deduplication keeps the first spelling the user typed, so ["Bug", "bug"]
    stores as ["Bug"] rather than inventing a canonical casing they never used.
    """
    if len(values) > MAX_TAGS:
        raise ValueError(f"at most {MAX_TAGS} tags allowed")

    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = value.strip()
        if not stripped:
            raise ValueError("tags must not be blank")
        if len(stripped) > MAX_TAG_LENGTH:
            raise ValueError(f"each tag must be at most {MAX_TAG_LENGTH} characters")
        key = stripped.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(stripped)
    return cleaned


def today_utc() -> date:
    """Today's calendar date in UTC.

    Overdue is judged against UTC because created_at/updated_at are UTC too;
    using the server's local date would make the rule depend on where the
    process happens to run.

    Returns:
        Today's date in UTC.
    """
    return datetime.now(timezone.utc).date()


def compute_is_overdue(due_date: Optional[date], status: TaskStatus) -> bool:
    """A task is overdue when its due date has already passed and it is not Done.

    Deliberate choices (see docs/midcourse/mini-adr.md):
    - No due date -> never overdue.
    - Due *today* is not overdue; you still have the day to finish it.
    - Done tasks are never overdue, even if completed late. The board uses
      "overdue" to mean "needs attention now", and finished work does not.

    Args:
        due_date: The task's due date, or None if it has none.
        status: The task's current status.

    Returns:
        True only when a due date exists, is strictly before today in UTC, and
        the status is not `Done`.
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
    tags: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _validate_title(value)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, values: list[str]) -> list[str]:
        return _validate_tags(values)


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee: Optional[str] = None
    due_date: Optional[date] = None
    tags: Optional[list[str]] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return _validate_title(value)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, values: Optional[list[str]]) -> list[str]:
        # An explicit `"tags": null` means "remove them all"; tags are never null
        # on a stored task, only empty. Omitting the key leaves them untouched.
        if values is None:
            return []
        return _validate_tags(values)


class TaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee: Optional[str]
    due_date: Optional[date] = None
    tags: list[str] = Field(default_factory=list)
    # Stamped by the storage layer on every read from the live comment store.
    # Not a computed field: the model cannot see storage, and storage importing
    # models (rather than the reverse) is the dependency direction we want.
    comment_count: int = 0
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_overdue(self) -> bool:
        """Derived on read, never stored — a stored flag would go stale at midnight."""
        return compute_is_overdue(self.due_date, self.status)


MAX_COMMENT_LENGTH = 2000
MAX_AUTHOR_LENGTH = 80


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str
    author: Optional[str] = None

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("comment body must not be blank")
        if len(stripped) > MAX_COMMENT_LENGTH:
            raise ValueError(f"comment body must be at most {MAX_COMMENT_LENGTH} characters")
        return stripped

    @field_validator("author")
    @classmethod
    def validate_author(cls, value: Optional[str]) -> Optional[str]:
        # A blank author is "anonymous", not a mistake — only an absurdly long
        # one is worth rejecting.
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if len(stripped) > MAX_AUTHOR_LENGTH:
            raise ValueError(f"author must be at most {MAX_AUTHOR_LENGTH} characters")
        return stripped


class CommentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    task_id: str
    author: Optional[str]
    body: str
    created_at: datetime


class ActivityKind(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    COMMENTED = "commented"
    DELETED = "deleted"


MAX_ACTIVITY_VALUE_LENGTH = 80


def describe_value(value: object) -> Optional[str]:
    """Flatten a task field value into a short string for the activity log.

    The log is heterogeneous — dates, enums, tag lists, free text — so every
    value is rendered as a string or as None. None and "empty" collapse to the
    same thing, which the timeline shows as "(none)": a task going from no tags
    to no tags is not a change anyone needs two spellings of.

    Long values are truncated, so pasting an essay into a description does not
    store a second copy of it in the log.

    Args:
        value: Any task field value — enum, date, list, string or None.

    Returns:
        A string preview, or None when the value is None or renders empty. A
        rendered value longer than `MAX_ACTIVITY_VALUE_LENGTH` is cut and
        suffixed with an ellipsis character.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) or None
    if isinstance(value, date):
        return value.isoformat()

    text = str(value)
    if not text:
        return None
    if len(text) > MAX_ACTIVITY_VALUE_LENGTH:
        return text[: MAX_ACTIVITY_VALUE_LENGTH - 1] + "…"
    return text


class ActivityEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    task_id: str
    # Snapshot of the task's title when the event happened, not a live lookup.
    # The board-wide feed outlives the tasks in it, so an entry for a deleted
    # task still has to say what it was called. A rename therefore leaves older
    # entries under the old name — which is what actually happened at the time.
    task_title: str
    kind: ActivityKind
    # `field` is set for `updated` entries only; `to_value` carries a preview of
    # the comment for `commented` entries.
    field: Optional[str] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    at: datetime
