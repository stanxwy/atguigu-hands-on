import type { ProjectStatus, ReportStatus, SourceType } from './enums';

export interface ProjectListItem {
  id: number;
  project_name: string;
  source_type: SourceType;
  project_status: ProjectStatus;
  last_started_at: string | null;
  last_finished_at: string | null;
}

export interface ProjectCreateRequest {
  project_name: string;
  source_type: SourceType;
  source_path: string;
  task_content?: string | null;
}

export interface ProjectCreateResult {
  id: number;
  project_name: string;
  source_type: SourceType;
  source_path: string;
  task_content: string | null;
  project_status: ProjectStatus;
  created_at: string;
}

export interface ProjectDetail {
  id: number;
  project_name: string;
  source_type: SourceType;
  source_path: string;
  task_content: string | null;
  project_status: ProjectStatus;
  vuln_count: number;
  attack_path_count: number;
  report_status: ReportStatus;
  created_at: string;
  updated_at: string;
}

export interface ProjectStatusResult {
  project_id: number;
  project_status: ProjectStatus;
}

export interface ProjectDeleteResult {
  deleted_project_id: number;
}

export interface ProjectListParams {
  page?: number;
  page_size?: number;
  project_status?: ProjectStatus | '';
}
