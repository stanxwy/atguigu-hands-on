import type {
  LogLevel,
  MessageType,
  ProjectStatus,
  ReportStatus,
  RiskLevel,
  SourceType,
  StageName,
  StageStatus,
  TaskStatus,
  VerifyStatus,
  WorkerRole,
} from '@/types/enums';

/** 枚举显示文案统一映射（中文，值为与后端一致的枚举字符串）。 */

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  created: '已创建',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  stopped: '已停止',
};

export const STAGE_NAME_LABELS: Record<StageName, string> = {
  environment_scan: '环境扫描',
  code_analysis: '代码分析',
  vulnerability_verify: '漏洞验证',
  report_generate: '报告生成',
  done: '完成',
};

export const STAGE_STATUS_LABELS: Record<StageStatus, string> = {
  pending: '待执行',
  running: '运行中',
  success: '成功',
  failed: '失败',
};

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  idle: '待执行',
  running: '运行中',
  success: '成功',
  failed: '失败',
};

export const VERIFY_STATUS_LABELS: Record<VerifyStatus, string> = {
  unverified: '未验证',
  verifying: '验证中',
  verified: '已验证',
  failed: '失败',
};

export const RISK_LEVEL_LABELS: Record<RiskLevel, string> = {
  critical: '严重',
  high: '高危',
  medium: '中危',
  low: '低危',
};

export const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  local_path: '本地路径',
  git_repo: 'Git 仓库',
};

export const REPORT_STATUS_LABELS: Record<ReportStatus, string> = {
  none: '未生成',
  generated: '已生成',
};

export const LOG_LEVEL_LABELS: Record<LogLevel, string> = {
  debug: '调试',
  info: '信息',
  warn: '警告',
  error: '错误',
};

export const MESSAGE_TYPE_LABELS: Record<MessageType, string> = {
  info: '信息',
  warning: '警告',
  error: '错误',
  critical: '严重',
  success: '成功',
};

export const WORKER_ROLE_LABELS: Record<WorkerRole, string> = {
  generic: '通用处理',
  env_check: '环境检查',
  code_analyze: '代码分析',
  vuln_verify: '漏洞验证',
  report_gen: '报告整理',
  ops: '运维辅助',
};
