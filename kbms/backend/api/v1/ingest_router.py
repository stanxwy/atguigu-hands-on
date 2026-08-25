import logging
import os
from datetime import datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)

from app.api.v1.deps import get_ingestion_service
from app.schema.ingestion_schema import IngestionResponse
from app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingest"])

@router.post("/upload", summary="file upload API", description="multiple files upload supported, triggers import workflow")
async def upload_files(background_tasks: BackgroundTasks, files: list[UploadFile] = File(...), service: IngestionService = Depends(get_ingestion_service)):
    try:
        data_based_root_dir = os.getenv("DATA_BASED_ROOT_DIR")
        date_str = datetime.now().strftime("%Y%m%d")
        date_dir = os.path.join(data_based_root_dir, date_str)
        task_ids = []
    
        for file in files:
            task_id, task_dir, import_file_path = service.upload_doc(date_str, date_dir, file)
            task_ids.append(task_id)

            background_tasks.add_task(service.run_graph_task, task_id, task_dir, import_file_path)
            logger.info(f"[{task_id}] Import Workflow task submitted to background executor")
    
        logger.info(f"File upload complete, total: {len(files)} files, tasks: {task_ids}")
        return IngestionResponse(code=200, message=f"{len(files)} files uploaded successfully", task_ids=task_ids)
    except Exception as e:
        logger.exception(f"Error uploading files: {e!s}", stack_info=True)
        raise HTTPException(status_code=500, detail=str(e))


