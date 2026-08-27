import type { StageName, TaskStatus, WorkerRole } from './enums';

export interface WorkerTaskItem {
  id: number;
  worker_role: WorkerRole;
  task_status: TaskStatus;
  stage_name: StageName | null;
  started_at: string | null;
  finished_at: string | null;
}
