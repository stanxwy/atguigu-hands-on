import type { StageName, StageStatus } from './enums';

export interface StageItem {
  stage_name: StageName;
  stage_status: StageStatus;
  started_at: string | null;
  finished_at: string | null;
}
