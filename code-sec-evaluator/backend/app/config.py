"""应用配置模块。

使用 pydantic-settings 从环境变量 / ``.env`` 文件读取配置。``SECRET_KEY``
无默认值，缺失即拒绝启动（对齐《安全规范》§3.2.2「密钥管理」）。
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置（环境变量 + .env 覆盖）。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- 安全 ----
    # 无默认值：缺失即启动失败（安全基线 AA-02）
    secret_key: str
    jwt_issuer: str = "code-sec-evaluator"
    jwt_audience: str = "code-sec-evaluator-api"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # ---- 数据层 ----
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    # ---- 工作区与文件 ----
    workspace_root: str = "./workspace"
    report_root: str = "./reports"
    log_root: str = "./runtime_logs"

    # ---- 隔离环境（作为 system_config 种子与兜底）----
    isolation_default_image: str = "sec-evaluator:latest"
    isolation_mount_readonly: bool = True
    isolation_network_mode: str = "none"
    # 本地回退开关（true=不创建容器，宿主机只读扫描，仅开发/演示；生产必须 false）
    isolation_fallback_local: bool = True

    # ---- 任务 ----
    task_default_timeout_seconds: int = 1800
    task_max_concurrency: int = 2

    # ---- 保留 ----
    retention_days: int = 30

    # ---- LLM 分析（默认关闭；开启后作为规则预筛之上的语义增强层）----
    llm_enabled: bool = False
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 120
    llm_max_retries: int = 2
    llm_temperature: float = 0.1

    # ---- 跨域 ----
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def workspace_path(self) -> Path:
        """返回规范化后的工作区根目录绝对路径。"""
        return Path(self.workspace_root).expanduser().resolve()

    @property
    def report_path(self) -> Path:
        """返回规范化后的报告根目录绝对路径。"""
        return Path(self.report_root).expanduser().resolve()

    @property
    def log_path(self) -> Path:
        """返回规范化后的运行日志根目录绝对路径。"""
        return Path(self.log_root).expanduser().resolve()


settings = Settings()
