# app/domain/ports/task_repository.py
from abc import ABC, abstractmethod

from app.domain.models.task import Task


class TaskRepository(ABC):

    @abstractmethod
    def create(self, task: Task) -> None: ...

    @abstractmethod
    def get(self, task_id: str) -> Task | None: ...

    @abstractmethod
    def update_status(self, task_id: str, status: str) -> None: ...

    @abstractmethod
    def add_done_step(self, task_id: str, step: str) -> None: ...

    @abstractmethod
    def add_running_step(self, task_id: str, step: str) -> None: ...

    @abstractmethod
    def set_error(self, task_id: str, error: str) -> None: ...

    @abstractmethod
    def delete(self, task_id: str) -> None: ...