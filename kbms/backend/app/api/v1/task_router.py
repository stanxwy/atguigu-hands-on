import logging
from typing import Any

from fastapi import (
    APIRouter,
)

from app.utils.task_utils import (
    get_done_task_list,
    get_running_task_list,
    get_task_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["task"])

@router.get("/status/{task_id}", summary="query task status", description="query task status with steps running/done by task_id")
async def get_task_progress(task_id: str):
    task_status_info: dict[str, Any] = {
        "code": 200,
        "task_id": task_id,
        "status": get_task_status(task_id),             # pending/processing/completed/failed
        "done_list": get_done_task_list(task_id),  
        "running_list": get_running_task_list(task_id)
    }
    logger.info(
        f"[{task_id}] task status {task_status_info['status']}, steps done: {task_status_info['done_list']}")
    return task_status_info