# services/query_service.py

import logging
import uuid
from typing import Any

from app.domain.ports.doc_store import DocumentStore
from app.utils.sse_utils import SSEEvent, create_sse_queue, push_sse_event
from app.utils.task_utils import (
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_PROCESSING,
    get_done_task_list,
    get_running_task_list,
    get_task_result,
    get_task_status,
    update_task_status,
)
from app.workflows.query.main_graph import KBQueryWorkflow

logger = logging.getLogger(__name__)

class QueryService:
    def __init__(self, doc_store: DocumentStore,
        workflow: KBQueryWorkflow):
        self._doc_store = doc_store
        self._workflow = workflow

    def generate_session_id(self) -> str:
        return str(uuid.uuid4())

    def generate_task_id(self) -> str:
        return str(uuid.uuid4())

    def init_task(self, task_id: str, session_id: str, is_stream: bool):
        update_task_status(task_id, TASK_STATUS_PROCESSING)
        if is_stream:
            create_sse_queue(session_id)

    def run_graph_task(self, task_id: str, session_id: str, user_query: str, is_stream: bool):
        logger.info(f"[{task_id} | {session_id}] Query Workflow started: {user_query}")
        try:
            init_state = {
                "original_query": user_query,
                "session_id": session_id,
                "task_id": task_id,
                "is_stream": is_stream,
            }
            self._workflow.run(init_state)

            if is_stream:
                push_sse_event(session_id, SSEEvent.PROGRESS, {
                    "status": get_task_status(task_id),
                    "done_list": get_done_task_list(task_id),
                    "running_list": get_running_task_list(task_id),
                })
            logger.info(f"[{session_id}] Query Workflow task completed")
            update_task_status(task_id, TASK_STATUS_COMPLETED, is_stream)
        except Exception as e:
            logger.exception(f"[{task_id} | {session_id}] error running Query Workflow task: {e!s}", stack_info=True)
            update_task_status(task_id, TASK_STATUS_FAILED, is_stream)
            if is_stream:
                push_sse_event(session_id, SSEEvent.ERROR, {"error": str(e)})

    def get_answer(self, task_id: str) -> str:
        return get_task_result(task_id, "answer", "")

    def get_history(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        records = self._doc_store.get_recent_messages(session_id, limit=limit)
        return [
            {
                "_id": str(r.get("_id", "")),
                "session_id": r.get("session_id", ""),
                "role": r.get("role", ""),
                "text": r.get("text", ""),
                "rewritten_query": r.get("rewritten_query", ""),
                "item_names": r.get("item_names", []),
                "ts": r.get("ts"),
            }
            for r in records
        ]

    def clear_history(self, session_id: str) -> int:
        return self._doc_store.clear_history(session_id)