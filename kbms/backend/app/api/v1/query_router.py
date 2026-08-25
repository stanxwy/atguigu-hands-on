import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.v1.deps import get_query_service
from app.schema.query_schema import QueryRequest, QueryResponse, StreamSubmitResponse
from app.services.query_service import QueryService
from app.utils.sse_utils import (
    sse_generator,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])

@router.post("/query")
async def query(background_tasks: BackgroundTasks, request: QueryRequest, service: QueryService = Depends(get_query_service)):
    try:
        is_stream = request.is_stream
        user_query = request.query
        session_id = request.session_id or service.generate_session_id()
        task_id = service.generate_task_id()
        service.init_task(task_id, session_id, is_stream)

        if is_stream:
            background_tasks.add_task(service.run_graph_task, task_id, session_id, user_query, is_stream)
            logger.info(f"[{task_id} | {session_id}] Query Workflow task submitted to background executor")

            return StreamSubmitResponse(
                message="Task submitted", session_id=session_id, task_id=task_id
            )
        else:
            service.run_graph_task(task_id, session_id, user_query, is_stream)
            return QueryResponse(
                message="Task completed", 
                session_id=session_id, 
                answer=service.get_answer(task_id)
            )
    except Exception as e:
        logger.exception(f"Error running Query Workflow task: {e!s}", stack_info=True)
        raise HTTPException(status_code=500, detail=f"Error running Query Workflow task: {e}")


@router.get("/stream/{session_id}")
async def stream(session_id: str, request: Request):
    logger.info(f"{session_id} started streaming...")
    logger.info(request)
    return StreamingResponse(
        sse_generator(session_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str, queryService: QueryService = Depends(get_query_service)):
    count = queryService.clear_history(session_id)
    return {"message": "Message history cleared", "deleted_count": count}

@router.get("/history/{session_id}")
async def history(session_id: str, limit: int = 50, queryService: QueryService = Depends(get_query_service)):
    try:
        items = queryService.get_history(session_id, limit)
        return {"session_id": session_id, "items": items}
    except Exception as e:
        logger.exception(f"history error: {e!s}", stack_info=True)
        raise HTTPException(status_code=500, detail=f"history error: {e}")
