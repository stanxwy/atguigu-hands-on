# app/domain/models/task.py
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Task:
    def __init__(
        self,
        task_id: str,
        status: TaskStatus = TaskStatus.PENDING,
        done_steps: list[str] | None = None,
        running_steps: list[str] | None = None,
        error: str | None = None,
        created_at: datetime | None = None,
    ):
        self.task_id = task_id
        self.status = status
        self.done_steps = done_steps or []
        self.running_steps = running_steps or []
        self.error = error
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "done_steps": self.done_steps,
            "running_steps": self.running_steps,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }