from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth_router import router as auth_router
from app.api.middleware.cors import setup_cors
from app.api.middleware.request_logger import request_logger_middleware
from app.api.org_router import router as org_router
from app.api.responses import domain_error_handler, validation_error_handler
from app.api.ui_router import router as ui_router
from app.api.v1.health_router import router as health_router
from app.api.v1.ingest_router import router as ingest_router
from app.api.v1.query_router import router as query_router
from app.api.v1.task_router import router as task_router
from app.domain.exceptions import DomainError
from app.infra.config.settings import get_settings
from app.utils.logger import setup_logging

load_dotenv(override=True)
settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
)

app.middleware("http")(request_logger_middleware)
setup_cors(app, settings.BACKEND_CORS_ORIGINS)

# 统一响应包：将 DomainError 映射为 {code, message, detail} + 对应 HTTP 状态（SPEC §8）。
app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)


STATIC_ROOT = Path(__file__).parent / "static"
app.mount(
    "/static",
    StaticFiles(directory=STATIC_ROOT),
    name="static",
)
app.include_router(health_router)
app.include_router(ui_router)
app.include_router(ingest_router, prefix=settings.API_V1_STR)
app.include_router(query_router, prefix=settings.API_V1_STR)
app.include_router(task_router, prefix=settings.API_V1_STR)
# 新路由统一前缀 /api（SPEC §3.1 / §5.2）。
app.include_router(auth_router, prefix=settings.API_STR)
app.include_router(org_router, prefix=settings.API_STR)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={
                "code": 40400,
                "message": "资源不存在",
                "detail": request.url.path,
            },
        )

    html_path = STATIC_ROOT / "pages" / "404.html"
    return FileResponse(html_path, status_code=404)

if __name__ == "__main__":
    uvicorn.run(
        app=app, # "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.env != "prod",
    )