"""项目接口请求/响应模型（对齐 openapi.yaml components/schemas Project*）。"""

import os
import re
from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from app.schemas import StrictModel

# 仅允许 HTTPS 公开仓库地址（安全规范 §2.2.2 / §2.7）
GIT_URL_RE = re.compile(r"^https://[^\s]+\.git$")


class ProjectCreate(StrictModel):
    """创建项目请求体。"""

    project_name: str = Field(..., min_length=1, max_length=128)
    source_type: Literal["local_path", "git_repo"]
    source_path: str = Field(..., min_length=1, max_length=512)
    task_content: str | None = Field(default=None, max_length=4096)

    @field_validator("project_name")
    @classmethod
    def _no_control_chars(cls, value: str) -> str:
        if any(ord(ch) < 32 for ch in value):
            raise ValueError("project_name 含非法控制字符")
        return value

    @field_validator("source_path")
    @classmethod
    def _validate_source(cls, value: str, info) -> str:
        source_type = info.data.get("source_type")
        if source_type == "git_repo" and not GIT_URL_RE.match(value):
            raise ValueError("git_repo 必须为 https:// 开头的 .git 地址")
        if source_type == "local_path" and not os.path.isabs(value):
            raise ValueError("local_path 必须为绝对路径")
        return value


class ProjectOut(StrictModel):
    """项目响应体（ORM 序列化）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_name: str
    source_type: str
    source_path: str
    task_content: str | None = None
    project_status: str
    created_at: datetime
    updated_at: datetime


class ProjectListItem(StrictModel):
    """项目列表项。"""

    id: int
    project_name: str
    source_type: str
    project_status: str
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None


class ProjectDetailOut(StrictModel):
    """项目详情响应（含派生统计）。"""

    id: int
    project_name: str
    source_type: str
    source_path: str
    task_content: str | None = None
    project_status: str
    vuln_count: int = 0
    attack_path_count: int = 0
    report_status: str = "none"
    created_at: datetime
    updated_at: datetime


class ProjectStatusOut(StrictModel):
    """启动/停止返回数据。"""

    project_id: int
    project_status: str


class ProjectDeleteOut(StrictModel):
    """删除返回数据。"""

    deleted_project_id: int
