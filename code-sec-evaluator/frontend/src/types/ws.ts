import type {
  LogLevel,
  MessageType,
  ProjectStatus,
  RiskLevel,
  StageName,
  StageStatus,
  TaskStatus,
  WorkerRole,
} from './enums';

export const WS_MESSAGE_TYPES = [
  'project_status',
  'stage_status',
  'worker_status',
  'chat_message',
  'runtime_log',
  'resource_usage',
  'vulnerability_found',
  'report_ready',
] as const;
export type WsMessageType = (typeof WS_MESSAGE_TYPES)[number];

export interface WsProjectStatusData {
  project_status: ProjectStatus;
}

export interface WsStageStatusData {
  stage_name: StageName;
  stage_status: StageStatus;
}

export interface WsWorkerStatusData {
  worker_task_id: number;
  worker_role: WorkerRole;
  task_status: TaskStatus;
}

export interface WsChatMessageData {
  worker_role: WorkerRole;
  message_type: MessageType;
  message_text: string;
}

export interface WsRuntimeLogData {
  log_level: LogLevel;
  log_content: string;
  created_at?: string;
}

export interface WsResourceUsageData {
  cpu_usage: number | null;
  memory_usage: number | null;
  token_count: number | null;
  recorded_at?: string;
}

export interface WsVulnerabilityFoundData {
  vuln_id: number;
  vuln_title: string;
  risk_level: RiskLevel;
}

export interface WsReportReadyData {
  report_id: number;
}

export interface WsEnvelopeBase {
  type: WsMessageType;
  project_id: number;
  timestamp: string;
}

export type WsEnvelope =
  | (WsEnvelopeBase & { type: 'project_status'; data: WsProjectStatusData })
  | (WsEnvelopeBase & { type: 'stage_status'; data: WsStageStatusData })
  | (WsEnvelopeBase & { type: 'worker_status'; data: WsWorkerStatusData })
  | (WsEnvelopeBase & { type: 'chat_message'; data: WsChatMessageData })
  | (WsEnvelopeBase & { type: 'runtime_log'; data: WsRuntimeLogData })
  | (WsEnvelopeBase & { type: 'resource_usage'; data: WsResourceUsageData })
  | (WsEnvelopeBase & { type: 'vulnerability_found'; data: WsVulnerabilityFoundData })
  | (WsEnvelopeBase & { type: 'report_ready'; data: WsReportReadyData });
