"""应用入口：挂载路由、CORS、WS、启动事件、异常处理器。

启动方式（backend/ 目录）：
    uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import projects, results, system, ws
from app.config import settings
from app.core.errors import AppError
from app.database import async_session_factory, init_models
from app.services import config_service
from app.services.llm_service import llm_service
from app.utils.logging import mask

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时：创建数据目录、建表并写入系统配置种子（失败不阻断启动）。"""
    for directory in (
        settings.workspace_path,
        settings.report_path,
        settings.log_path,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    try:
        await init_models()
        async with async_session_factory() as db:
            await config_service.seed_configs(db)
            await db.commit()
    except Exception as exc:  # noqa: BLE001  见说明
        logger.warning("启动初始化失败（可稍后运行 scripts/init_db.py 重试）: %s", exc)
    llm_service.reset()
    yield
    await llm_service.aclose()


app = FastAPI(
    title="自动化安全评估系统 API",
    version="1.0.0",
    description="代码安全评估系统后端（对齐 docs/openapi.yaml 契约基线）",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """附加基础安全响应头（CSP/HSTS 建议由反向代理配置，见安全规范 §4.2）。"""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


def _format_validation_detail(exc: RequestValidationError) -> str:
    """将 Pydantic 校验错误压缩为可读提示。"""
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(part) for part in first.get("loc", []) if part != "body")
    message = first.get("msg", "参数校验失败")
    return f"{loc}: {message}" if loc else message


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """业务异常统一转 ``{code, message, data}``。"""
    return JSONResponse(status_code=exc.http_status, content=exc.as_dict())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """请求参数校验失败统一为 1001 / HTTP 400。"""
    return JSONResponse(
        status_code=400,
        content={
            "code": 1001,
            "message": mask(_format_validation_detail(exc)),
            "data": None,
        },
    )


@app.exception_handler(Exception)
async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """未捕获异常统一为 5000 / HTTP 500。"""
    logger.exception("未捕获异常: %s", mask(str(exc)))
    return JSONResponse(
        status_code=500, content={"code": 5000, "message": "内部错误", "data": None}
    )


app.include_router(system.router)
app.include_router(projects.router)
app.include_router(results.router)
app.include_router(ws.router)


def _build_openapi_schema() -> dict[str, Any]:
    """暴露 OpenAPI schema 生成入口（供测试/探活使用）。"""
    return app.openapi()
