"""结果查询接口（对齐 SPEC §3.4 / openapi.yaml Result 标签）。

阶段 / 角色 / 漏洞 / 攻击路径 / 报告 / 日志 / 资源，全部挂在
``/api/projects/{project_id}`` 下并经 ``get_owned_project`` 归属校验。
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_owned_project
from app.core.errors import ok
from app.models.project import Project
from app.services import (
    attack_path_service,
    project_service,
    report_service,
    vulnerability_service,
)
from app.services.llm_service import llm_service
from app.services.monitor_service import monitor_service

router = APIRouter(prefix="/api/projects/{project_id}", tags=["Result"])


@router.get("/stages")
async def get_stages(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询阶段状态。"""
    return ok({"list": await project_service.get_stages(db, project.id)})


@router.get("/workers")
async def get_workers(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询角色执行状态。"""
    return ok({"list": await project_service.get_workers(db, project.id)})


@router.get("/vulnerabilities")
async def list_vulnerabilities(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
    risk_level: str | None = Query(None),
    verify_status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    """查询漏洞列表。"""
    total, rows = await vulnerability_service.list_vulnerabilities(
        db,
        project.id,
        risk_level=risk_level,
        verify_status=verify_status,
        page=page,
        page_size=page_size,
    )
    items = [
        {
            "id": v.id,
            "vuln_code": v.vuln_code,
            "vuln_title": v.vuln_title,
            "risk_level": v.risk_level,
            "file_path": v.file_path,
            "verify_status": v.verify_status,
            "created_at": v.created_at,
        }
        for v in rows
    ]
    return ok({"total": total, "list": items})


@router.get("/vulnerabilities/{vuln_id}")
async def get_vulnerability(
    vuln_id: int,
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询漏洞详情。"""
    vuln = await vulnerability_service.get_vulnerability(db, project.id, vuln_id)
    return ok(
        {
            "id": vuln.id,
            "vuln_code": vuln.vuln_code,
            "vuln_title": vuln.vuln_title,
            "risk_level": vuln.risk_level,
            "file_path": vuln.file_path,
            "condition_text": vuln.condition_text,
            "evidence_text": vuln.evidence_text,
            "verify_status": vuln.verify_status,
            "reproduce_steps_text": vuln.reproduce_steps_text,
            "verify_code_text": vuln.verify_code_text,
            "created_at": vuln.created_at,
        }
    )


@router.get("/attack-paths")
async def list_attack_paths(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询攻击路径列表。"""
    total, items = await attack_path_service.list_attack_paths(db, project.id)
    return ok({"total": total, "list": items})


@router.get("/attack-paths/{path_id}")
async def get_attack_path(
    path_id: int,
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询攻击路径详情。"""
    return ok(await attack_path_service.get_attack_path(db, project.id, path_id))


@router.get("/report")
async def get_report(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询最终报告（Markdown 权威 + HTML 派生）。"""
    report = await report_service.get_report(db, project.id)
    return ok(
        {
            "report_id": report.id,
            "report_markdown": report.report_markdown,
            "report_html": report.report_html,
            "created_at": report.created_at,
        }
    )


@router.get("/report/download")
async def download_report(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """下载报告文件（Markdown，不套统一响应封装）。"""
    report = await report_service.get_report(db, project.id)
    content = (report.report_markdown or "").encode("utf-8")
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="report-{project.id}.md"'},
    )


@router.get("/logs")
async def list_logs(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
    log_level: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    """查询运行日志。"""
    total, items = await monitor_service.list_logs(
        db,
        project.id,
        level=log_level,
        page=page,
        page_size=page_size,
    )
    return ok({"total": total, "list": items})


@router.get("/resources")
async def list_resources(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1),
) -> dict[str, Any]:
    """查询资源消耗（最近 N 条）。"""
    items = await monitor_service.list_resources(db, project.id, limit)
    return ok({"list": items})


@router.get("/llm-logs")
async def list_llm_logs(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
    task_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    """查询 LLM 调用日志（确认/验证/攻击路径/摘要审计记录）。"""
    total, items = await llm_service.list_logs(
        db, project.id, task_type=task_type, page=page, page_size=page_size
    )
    return ok({"total": total, "list": items})
