export interface IsolationConfig {
  default_image: string;
  mount_readonly: boolean;
  network_mode: string;
}

export interface TaskConfig {
  default_timeout_seconds: number;
  max_concurrency: number;
}

export interface RetentionConfig {
  days: number;
}

export interface LLMConfig {
  enabled: boolean;
  base_url: string;
  api_key: string;
  api_key_configured: boolean;
  model: string;
}

export interface SystemConfig {
  isolation: IsolationConfig;
  task: TaskConfig;
  retention: RetentionConfig;
  llm: LLMConfig;
}

/** 更新配置请求体：扁平键值对（如 task.max_concurrency）。 */
export type ConfigUpdates = Record<string, string | number | boolean>;

/** 更新响应：仅包含被更新分组的嵌套片段。 */
export interface ConfigUpdateResult {
  isolation?: IsolationConfig;
  task?: TaskConfig;
  retention?: RetentionConfig;
  llm?: LLMConfig;
}
