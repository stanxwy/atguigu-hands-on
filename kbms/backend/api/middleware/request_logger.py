import logging
import time

from fastapi import Request

logger = logging.getLogger(__name__)

async def request_logger_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    logger.debug(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response