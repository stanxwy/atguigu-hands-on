/**
 * 枚举常量与联合类型（与后端 core/constants.py、数据库枚举值严格对齐，
 * 值保持 snake_case，禁止自定义扩展值）。
 */

export const SOURCE_TYPES = ['local_path', 'git_repo'] as const;
export type SourceType = (typeof SOURCE_TYPES)[number];

export const PROJECT_STATUSES = ['created', 'running', 'completed', 'failed', 'stopped'] as const;
export type ProjectStatus = (typeof PROJECT_STATUSES)[number];

export const STAGE_NAMES = [
  'environment_scan',
  'code_analysis',
  'vulnerability_verify',
  'report_generate',
  'done',
] as const;
export type StageName = (typeof STAGE_NAMES)[number];

export const STAGE_STATUSES = ['pending', 'running', 'success', 'failed'] as const;
export type StageStatus = (typeof STAGE_STATUSES)[number];

export const WORKER_ROLES = [
  'generic',
  'env_check',
  'code_analyze',
  'vuln_verify',
  'report_gen',
  'ops',
] as const;
export type WorkerRole = (typeof WORKER_ROLES)[number];

export const TASK_STATUSES = ['idle', 'running', 'success', 'failed'] as const;
export type TaskStatus = (typeof TASK_STATUSES)[number];

export const RISK_LEVELS = ['critical', 'high', 'medium', 'low'] as const;
export type RiskLevel = (typeof RISK_LEVELS)[number];

export const VERIFY_STATUSES = ['unverified', 'verifying', 'verified', 'failed'] as const;
export type VerifyStatus = (typeof VERIFY_STATUSES)[number];

export const LOG_LEVELS = ['debug', 'info', 'warn', 'error'] as const;
export type LogLevel = (typeof LOG_LEVELS)[number];

export const MESSAGE_TYPES = ['info', 'warning', 'error', 'critical', 'success'] as const;
export type MessageType = (typeof MESSAGE_TYPES)[number];

export const USER_ROLES = ['admin', 'user'] as const;
export type UserRole = (typeof USER_ROLES)[number];

export const USER_STATUSES = ['active', 'disabled'] as const;
export type UserStatus = (typeof USER_STATUSES)[number];

export const REPORT_STATUSES = ['none', 'generated'] as const;
export type ReportStatus = (typeof REPORT_STATUSES)[number];
