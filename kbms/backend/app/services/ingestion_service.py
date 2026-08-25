import logging
import os
import shutil
import uuid

from app.domain.ports.object_store import ObjectStore
from app.utils.task_utils import (
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_PROCESSING,
    add_done_task,
    add_running_task,
    update_task_status,
)
from app.workflows.ingestion.main_graph import KBImportWorkflow

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self, object_store: ObjectStore,
        workflow: KBImportWorkflow):
        self._object_store = object_store
        self._workflow = workflow

    def generate_task_id(self) -> str:
        return str(uuid.uuid4())

    def upload_doc(self, date_str, date_dir, file):
        task_id = self.generate_task_id()
        add_running_task(task_id, "upload_file")
        logger.info(f"[{task_id}] start processing upload file: {file.filename}, file type: {file.content_type}")

        task_dir = os.path.join(date_dir, task_id)
        os.makedirs(task_dir, exist_ok=True)
        import_file_path = os.path.join(task_dir, file.filename)

        with open(import_file_path, "wb") as file_buffer:
            shutil.copyfileobj(file.file, file_buffer)
        logger.info(f"[{task_id}] file saved to local, path: {import_file_path}")

        object_name = f"doc/{date_str}/{file.filename}"
        try:
            url = self._object_store.upload(import_file_path, object_name, file.content_type)
            
            logger.info(f"[{task_id}] file uploaded, url: {url}")
        except Exception as e:
            logger.warning(f"[{task_id}] error uploading file: {e!s}", stack_info=True)

        add_done_task(task_id, "upload_file")
        return task_id, task_dir, import_file_path
    
    def run_graph_task(self, task_id: str, output_file_dir: str, import_file_path: str):
        logger.info(f"[{task_id}] Ingestion Workflow started: {import_file_path}")
        
        try:
            update_task_status(task_id, TASK_STATUS_PROCESSING)

            init_state = {
                "task_id": task_id,
                "import_file_path": import_file_path,
                "output_file_dir": output_file_dir,
            }

            for event in self._workflow.run(init_state, stream=True):
                for node_name, node_result in event.items():
                    result_str = str(node_result)
                    logger.info(f"[{task_id}] {node_name}\n{result_str[:200]}")
                    add_done_task(task_id, node_name)

            update_task_status(task_id, TASK_STATUS_COMPLETED)

        except Exception as e:
            logger.exception(f"[{task_id}] error running Ingestion Workflow task: {e!s}", stack_info=True)
            update_task_status(task_id, TASK_STATUS_FAILED)

