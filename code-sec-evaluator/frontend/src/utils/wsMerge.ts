import type { StageItem } from '@/types/stage';
import type { WorkerTaskItem } from '@/types/worker';
import type { WsStageStatusData, WsWorkerStatusData } from '@/types/ws';

/** 将 WS 阶段事件合并进本地阶段列表（按 stage_name 幂等合并）。 */
export function mergeStageEvents(stages: StageItem[], events: WsStageStatusData[]): StageItem[] {
  const next = [...stages];
  for (const event of events) {
    const index = next.findIndex((stage) => stage.stage_name === event.stage_name);
    if (index >= 0) {
      next[index] = { ...next[index], stage_status: event.stage_status };
    } else {
      next.push({
        stage_name: event.stage_name,
        stage_status: event.stage_status,
        started_at: null,
        finished_at: null,
      });
    }
  }
  return next;
}

/** 将 WS 角色事件合并进本地角色列表（按 worker_task_id 幂等合并）。 */
export function mergeWorkerEvents(
  workers: WorkerTaskItem[],
  events: WsWorkerStatusData[],
): WorkerTaskItem[] {
  const next = [...workers];
  for (const event of events) {
    const index = next.findIndex((worker) => worker.id === event.worker_task_id);
    if (index >= 0) {
      next[index] = {
        ...next[index],
        worker_role: event.worker_role,
        task_status: event.task_status,
      };
    } else {
      next.push({
        id: event.worker_task_id,
        worker_role: event.worker_role,
        task_status: event.task_status,
        stage_name: null,
        started_at: null,
        finished_at: null,
      });
    }
  }
  return next;
}
