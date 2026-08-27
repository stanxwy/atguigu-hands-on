import type { ConfigUpdateResult, ConfigUpdates, SystemConfig } from '@/types/config';

import { request } from './client';

/** 查询系统配置（管理员）。 */
export function getConfig(): Promise<SystemConfig> {
  return request<SystemConfig>({ url: '/system/config', method: 'get' });
}

/** 更新系统配置（管理员），返回被更新分组的配置片段。 */
export function updateConfig(updates: ConfigUpdates): Promise<ConfigUpdateResult> {
  return request<ConfigUpdateResult>({
    url: '/system/config',
    method: 'put',
    data: { config: updates },
  });
}
