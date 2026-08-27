import type { Paginated } from '@/types/api';
import type { AttackPathDetail, AttackPathListItem } from '@/types/attackPath';
import type { LogLevel } from '@/types/enums';
import type { RuntimeLogItem } from '@/types/log';
import type { ReportData } from '@/types/report';
import type { ResourceUsageItem } from '@/types/resource';
import type { StageItem } from '@/types/stage';
import type {
  VulnerabilityDetail,
  VulnerabilityListItem,
  VulnerabilityListParams,
} from '@/types/vulnerability';
import type { WorkerTaskItem } from '@/types/worker';

import { client, request } from './client';

/** 查询阶段状态。 */
export function getStages(projectId: number): Promise<{ list: StageItem[] }> {
  return request<{ list: StageItem[] }>({ url: `/projects/${projectId}/stages`, method: 'get' });
}

/** 查询角色执行状态。 */
export function getWorkers(projectId: number): Promise<{ list: WorkerTaskItem[] }> {
  return request<{ list: WorkerTaskItem[] }>({
    url: `/projects/${projectId}/workers`,
    method: 'get',
  });
}

/** 分页查询漏洞列表（可按风险等级/验证状态过滤）。 */
export function listVulnerabilities(
  projectId: number,
  params: VulnerabilityListParams = {},
): Promise<Paginated<VulnerabilityListItem>> {
  return request<Paginated<VulnerabilityListItem>>({
    url: `/projects/${projectId}/vulnerabilities`,
    method: 'get',
    params,
  });
}

/** 查询漏洞详情。 */
export function getVulnerability(projectId: number, vulnId: number): Promise<VulnerabilityDetail> {
  return request<VulnerabilityDetail>({
    url: `/projects/${projectId}/vulnerabilities/${vulnId}`,
    method: 'get',
  });
}

/** 查询攻击路径列表。 */
export function listAttackPaths(projectId: number): Promise<Paginated<AttackPathListItem>> {
  return request<Paginated<AttackPathListItem>>({
    url: `/projects/${projectId}/attack-paths`,
    method: 'get',
  });
}

/** 查询攻击路径详情（含按顺序的漏洞明细）。 */
export function getAttackPath(projectId: number, pathId: number): Promise<AttackPathDetail> {
  return request<AttackPathDetail>({
    url: `/projects/${projectId}/attack-paths/${pathId}`,
    method: 'get',
  });
}

/** 查询最终报告（Markdown 权威 + HTML 派生）。 */
export function getReport(projectId: number): Promise<ReportData> {
  return request<ReportData>({ url: `/projects/${projectId}/report`, method: 'get' });
}

/** 下载报告（Markdown 文件流，不套统一响应封装）。 */
export async function downloadReport(projectId: number): Promise<void> {
  const response = await client.get(`/projects/${projectId}/report/download`, {
    responseType: 'blob',
  });
  const blob = response.data as Blob;
  const disposition = response.headers['content-disposition'] as string | undefined;
  const filenameMatch = /filename="?([^";]+)"?/.exec(disposition ?? '');
  const filename = filenameMatch?.[1] ?? `report-${projectId}.md`;
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(objectUrl);
}

/** 分页查询运行日志（可按级别过滤）。 */
export function listLogs(
  projectId: number,
  params: { log_level?: LogLevel | ''; page?: number; page_size?: number } = {},
): Promise<Paginated<RuntimeLogItem>> {
  return request<Paginated<RuntimeLogItem>>({
    url: `/projects/${projectId}/logs`,
    method: 'get',
    params,
  });
}

/** 查询资源消耗（最近 N 条）。 */
export function listResources(
  projectId: number,
  limit = 100,
): Promise<{ list: ResourceUsageItem[] }> {
  return request<{ list: ResourceUsageItem[] }>({
    url: `/projects/${projectId}/resources`,
    method: 'get',
    params: { limit },
  });
}
