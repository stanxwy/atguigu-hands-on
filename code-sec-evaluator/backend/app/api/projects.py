"""项目生命周期接口：POST/GET /projects、GET/DELETE /projects/{id}、start/stop。"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_owned_project
from app.core.errors import ok
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.services import project_service
from app.services.scheduler import scheduler

router = APIRouter(prefix="/api/projects", tags=["Project"])


@router.post("")
async def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """创建评估项目（初始状态 created）。"""
    project = await project_service.create_project(db, user, payload)
    await db.commit()
    await db.refresh(project)
    return ok(
        {
            "id": project.id,
            "project_name": project.project_name,
            "source_type": project.source_type,
            "source_path": project.source_path,
            "task_content": project.task_content,
            "project_status": project.project_status,
            "created_at": project.created_at,
        }
    )


@router.get("")
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    project_status: str | None = Query(None),
) -> dict[str, Any]:
    """分页查询项目列表（可按状态过滤）。"""
    total, items = await project_service.list_projects(
        db,
        user,
        page=page,
        page_size=page_size,
        project_status=project_status,
    )
    return ok({"total": total, "list": items})


@router.get("/{project_id}")
async def get_project(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询项目详情（含漏洞/路径计数与报告状态）。"""
    return ok(await project_service.get_project_detail(db, project))


@router.delete("/{project_id}")
async def delete_project(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """删除项目：销毁容器 + 级联删除数据 + 清理文件目录。"""
    deleted_id = await project_service.delete_project(db, project)
    return ok({"deleted_project_id": deleted_id})


@router.post("/{project_id}/start")
async def start_project(
    project: Project = Depends(get_owned_project),
) -> dict[str, Any]:
    """启动评估任务（异步受理）。"""
    project = await scheduler.start(project.id)
    return ok({"project_id": project.id, "project_status": project.project_status})


@router.post("/{project_id}/stop")
async def stop_project(
    project: Project = Depends(get_owned_project),
) -> dict[str, Any]:
    """停止评估任务。"""
    project = await scheduler.stop(project.id)
    return ok({"project_id": project.id, "project_status": project.project_status})
