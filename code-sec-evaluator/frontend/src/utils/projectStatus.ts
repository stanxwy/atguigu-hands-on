import type { ProjectStatus } from '@/types/enums';

/** 允许启动评估的前置状态（对齐后端 constants.PROJECT_STARTABLE）。 */
const STARTABLE_STATUSES: readonly ProjectStatus[] = ['created', 'completed', 'failed', 'stopped'];

export function isProjectStartable(status: ProjectStatus): boolean {
  return STARTABLE_STATUSES.includes(status);
}

export function isProjectStoppable(status: ProjectStatus): boolean {
  return status === 'running';
}
