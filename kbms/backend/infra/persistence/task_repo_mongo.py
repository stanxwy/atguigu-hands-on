# app/infra/persistence/task_repo_mongo.py
import logging
from datetime import datetime

from pymongo.collection import Collection

from app.domain.models.task import Task, TaskStatus
from app.domain.ports.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class TaskRepositoryMongo(TaskRepository):
    def __init__(self, collection: Collection):
        self._col = collection

    def create(self, task: Task) -> None:
        self._col.insert_one(task.to_dict())

    def get(self, task_id: str) -> Task | None:
        doc = self._col.find_one({"task_id": task_id})
        if not doc:
            return None
        return Task(
            task_id=doc["task_id"],
            status=TaskStatus(doc["status"]),
            done_steps=doc.get("done_steps", []),
            running_steps=doc.get("running_steps", []),
            error=doc.get("error"),
            created_at=datetime.fromisoformat(doc["created_at"]),
        )

    def update_status(self, task_id: str, status: str) -> None:
        self._col.update_one(
            {"task_id": task_id},
            {"$set": {"status": status}}
        )

    def add_done_step(self, task_id: str, step: str) -> None:
        self._col.update_one(
            {"task_id": task_id},
            {"$addToSet": {"done_steps": step}}
        )

    def add_running_step(self, task_id: str, step: str) -> None:
        self._col.update_one(
            {"task_id": task_id},
            {"$addToSet": {"running_steps": step}}
        )

    def set_error(self, task_id: str, error: str) -> None:
        self._col.update_one(
            {"task_id": task_id},
            {"$set": {"status": TaskStatus.FAILED.value, "error": error}}
        )

    def delete(self, task_id: str) -> None:
        self._col.delete_one({"task_id": task_id})