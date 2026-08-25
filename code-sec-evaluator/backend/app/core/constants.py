"""枚举常量定义（对齐《SPEC》§2/§3 与《编码规范》§7 领域命名对照表）。

约定：数据库以 VARCHAR 存储枚举值，应用层以本模块常量约束（SPEC §2.1），
避免数据库枚举变更成本。
"""

# ---- 消息类型（5 值，注意与 log_level 区分）----
MESSAGE_TYPES: tuple[str, ...] = ("info", "warning", "error", "critical", "success")
MESSAGE_TYPE_SET: frozenset[str] = frozenset(MESSAGE_TYPES)

# ---- 风险等级（对齐 CVSS v3.1 区间）----
RISK_LEVELS: tuple[str, ...] = ("critical", "high", "medium", "low")
RISK_LEVEL_SET: frozenset[str] = frozenset(RISK_LEVELS)
# 用于排序的严重度权重（越大越严重）
RISK_SEVERITY: dict[str, int] = {"critical": 4, "high": 3, "medium": 2, "low": 1}

# ---- 验证状态 ----
VERIFY_STATUSES: tuple[str, ...] = ("unverified", "verifying", "verified", "failed")
VERIFY_STATUS_SET: frozenset[str] = frozenset(VERIFY_STATUSES)

# ---- 项目状态 ----
PROJECT_STATUSES: tuple[str, ...] = (
    "created",
    "running",
    "completed",
    "failed",
    "stopped",
)
PROJECT_STATUS_SET: frozenset[str] = frozenset(PROJECT_STATUSES)
# 允许启动评估的前置状态（SPEC §3.3.4）
PROJECT_STARTABLE: frozenset[str] = frozenset(
    {"created", "completed", "failed", "stopped"}
)

# ---- 阶段 ----
STAGE_NAMES: tuple[str, ...] = (
    "environment_scan",
    "code_analysis",
    "vulnerability_verify",
    "report_generate",
    "done",
)
STAGE_NAME_SET: frozenset[str] = frozenset(STAGE_NAMES)
# 阶段推进顺序（不含终态 done）
STAGE_ORDER: tuple[str, ...] = (
    "environment_scan",
    "code_analysis",
    "vulnerability_verify",
    "report_generate",
)
STAGE_STATUSES: tuple[str, ...] = ("pending", "running", "success", "failed")
STAGE_STATUS_SET: frozenset[str] = frozenset(STAGE_STATUSES)

# ---- 角色任务 ----
WORKER_ROLES: tuple[str, ...] = (
    "generic",
    "env_check",
    "code_analyze",
    "vuln_verify",
    "report_gen",
    "ops",
)
WORKER_ROLE_SET: frozenset[str] = frozenset(WORKER_ROLES)
TASK_STATUSES: tuple[str, ...] = ("idle", "running", "success", "failed")
TASK_STATUS_SET: frozenset[str] = frozenset(TASK_STATUSES)

# ---- 日志级别（与 message_type 区分）----
LOG_LEVELS: tuple[str, ...] = ("debug", "info", "warn", "error")
LOG_LEVEL_SET: frozenset[str] = frozenset(LOG_LEVELS)

# ---- 源码类型 ----
SOURCE_TYPES: tuple[str, ...] = ("local_path", "git_repo")
SOURCE_TYPE_SET: frozenset[str] = frozenset(SOURCE_TYPES)

# ---- 用户 ----
USER_ROLES: tuple[str, ...] = ("admin", "user")
USER_ROLE_SET: frozenset[str] = frozenset(USER_ROLES)
USER_STATUSES: tuple[str, ...] = ("active", "disabled")
USER_STATUS_SET: frozenset[str] = frozenset(USER_STATUSES)

# ---- 系统配置值类型 ----
CONFIG_TYPES: tuple[str, ...] = ("string", "int", "float", "bool", "json")
CONFIG_TYPE_SET: frozenset[str] = frozenset(CONFIG_TYPES)

# ---- 报告状态（派生字段，非独立表）----
REPORT_STATUS_NONE = "none"
REPORT_STATUS_GENERATED = "generated"

# ---- WebSocket 鉴权失败关闭码 ----
WS_UNAUTHORIZED_CODE = 4001

# ---- 阶段到角色的映射（调度器派发依据）----
STAGE_TO_ROLE: dict[str, str] = {
    "environment_scan": "env_check",
    "code_analysis": "code_analyze",
    "vulnerability_verify": "vuln_verify",
    "report_generate": "report_gen",
}
