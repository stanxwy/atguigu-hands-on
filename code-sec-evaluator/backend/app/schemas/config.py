"""系统配置接口请求/响应模型（对齐 openapi.yaml ConfigOut 等）。"""

from pydantic import Field

from app.schemas import StrictModel


class IsolationConfig(StrictModel):
    """隔离环境配置分组。"""

    default_image: str = ""
    mount_readonly: bool = True
    network_mode: str = "none"


class TaskConfig(StrictModel):
    """任务配置分组。"""

    default_timeout_seconds: int = 1800
    max_concurrency: int = 2


class RetentionConfig(StrictModel):
    """保留策略配置分组。"""

    days: int = 30


class ConfigOut(StrictModel):
    """系统配置整体响应。"""

    isolation: IsolationConfig = IsolationConfig()
    task: TaskConfig = TaskConfig()
    retention: RetentionConfig = RetentionConfig()


class ConfigUpdateRequest(StrictModel):
    """更新系统配置请求体。"""

    config: dict[str, str | int | float | bool] = Field(
        ..., description="键值对，键遵循 SPEC §2.5"
    )
