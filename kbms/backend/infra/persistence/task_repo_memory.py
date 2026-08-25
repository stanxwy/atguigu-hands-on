from app.domain.models.task import Task, TaskStatus
from app.domain.ports.task_repository import TaskRepository
from app.utils.task_utils import (
    add_done_task as _add_done_task,
)
from app.utils.task_utils import (
    add_running_task as _add_running_task,
)
from app.utils.task_utils import (
    clear_task as _clear_task,
)
from app.utils.task_utils import (
    create_task as _create_task,
)
from app.utils.task_utils import (
    get_task_status as _get_task_status,
)
from app.utils.task_utils import (
    update_task_status as _update_task_status,
)


class TaskRepositoryMemory(TaskRepository):
    def create(self, task: Task) -> None:
        _create_task(task.task_id)

    def get(self, task_id: str):
        data = _get_task_status(task_id)
        if not data:
            return None
        return Task(
            task_id=task_id,
            status=data["status"],
            done_steps=data.get("done_steps", []),
            running_steps=data.get("running_steps", []),
            error=data.get("error"),
        )

    def update_status(self, task_id: str, status: str) -> None:
        _update_task_status(task_id, status)

    def add_done_step(self, task_id: str, step: str) -> None:
        _add_done_task(task_id, step)

    def add_running_step(self, task_id: str, step: str) -> None:
        _add_running_task(task_id, step)

    def set_error(self, task_id: str, error: str) -> None:
        _update_task_status(task_id, "failed")
        # 你可以在 task_utils 里加一个 set_error 或直接复用
        from app.utils.task_utils import task_status
        if task_id in task_status:
            task_status[task_id]["error"] = error

    def delete(self, task_id: str) -> None:
        _clear_task(task_id)