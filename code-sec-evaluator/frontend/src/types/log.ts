import type { LogLevel } from './enums';

export interface RuntimeLogItem {
  id: number;
  log_level: LogLevel;
  log_content: string;
  stage_name: string | null;
  created_at: string;
}
