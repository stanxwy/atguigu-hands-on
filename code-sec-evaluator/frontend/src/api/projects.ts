import type { Paginated } from '@/types/api';
import type {
  ProjectCreateRequest,
  ProjectCreateResult,
  ProjectDeleteResult,
  ProjectDetail,
  ProjectListItem,
  ProjectListParams,
  ProjectStatusResult,
} from '@/types/project';

import { request } from './client';

/** 创建评估项目。 */
export function createProject(payload: ProjectCreateRequest): Promise<ProjectCreateResult> {
  return request<ProjectCreateResult>({ url: '/projects', method: 'post', data: payload });
}

/** 分页查询项目列表（可按状态过滤）。 */
export function listProjects(params: ProjectListParams = {}): Promise<Paginated<ProjectListItem>> {
  return request<Paginated<ProjectListItem>>({ url: '/projects', method: 'get', params });
}

/** 查询项目详情。 */
export function getProject(projectId: number): Promise<ProjectDetail> {
  return request<ProjectDetail>({ url: `/projects/${projectId}`, method: 'get' });
}

/** 启动评估任务。 */
export function startProject(projectId: number): Promise<ProjectStatusResult> {
  return request<ProjectStatusResult>({ url: `/projects/${projectId}/start`, method: 'post' });
}

/** 停止评估任务。 */
export function stopProject(projectId: number): Promise<ProjectStatusResult> {
  return request<ProjectStatusResult>({ url: `/projects/${projectId}/stop`, method: 'post' });
}

/** 删除项目（级联清理）。 */
export function deleteProject(projectId: number): Promise<ProjectDeleteResult> {
  return request<ProjectDeleteResult>({ url: `/projects/${projectId}`, method: 'delete' });
}
