import { create } from 'zustand';

import { getErrorMessage } from '@/api/client';
import {
  createProject as createProjectApi,
  deleteProject as deleteProjectApi,
  getProject as getProjectApi,
  listProjects as listProjectsApi,
  startProject as startProjectApi,
  stopProject as stopProjectApi,
} from '@/api/projects';
import type { AsyncStatus } from '@/types/api';
import type {
  ProjectCreateRequest,
  ProjectDetail,
  ProjectListItem,
  ProjectListParams,
} from '@/types/project';

interface ProjectState {
  list: ProjectListItem[];
  total: number;
  listStatus: AsyncStatus;
  listError: string | null;
  detail: ProjectDetail | null;
  detailStatus: AsyncStatus;
  detailError: string | null;
  operationStatus: AsyncStatus;
  operationError: string | null;
  fetchList: (params?: ProjectListParams) => Promise<void>;
  fetchDetail: (projectId: number) => Promise<void>;
  createProject: (payload: ProjectCreateRequest) => Promise<number | null>;
  startProject: (projectId: number) => Promise<boolean>;
  stopProject: (projectId: number) => Promise<boolean>;
  deleteProject: (projectId: number) => Promise<boolean>;
  resetDetail: () => void;
  resetOperationError: () => void;
}

/**
 * 项目状态：列表/详情/生命周期操作收敛于此，页面不散落请求逻辑。
 */
export const useProjectStore = create<ProjectState>((set) => ({
  list: [],
  total: 0,
  listStatus: 'idle',
  listError: null,
  detail: null,
  detailStatus: 'idle',
  detailError: null,
  operationStatus: 'idle',
  operationError: null,
  fetchList: async (params = {}) => {
    set({ listStatus: 'loading', listError: null });
    try {
      const result = await listProjectsApi(params);
      set({ list: result.list, total: result.total, listStatus: 'success' });
    } catch (error) {
      set({ listStatus: 'error', listError: getErrorMessage(error) });
    }
  },
  fetchDetail: async (projectId) => {
    set({ detailStatus: 'loading', detailError: null });
    try {
      const detail = await getProjectApi(projectId);
      set({ detail, detailStatus: 'success' });
    } catch (error) {
      set({ detailStatus: 'error', detailError: getErrorMessage(error) });
    }
  },
  createProject: async (payload) => {
    set({ operationStatus: 'loading', operationError: null });
    try {
      const created = await createProjectApi(payload);
      set({ operationStatus: 'success' });
      return created.id;
    } catch (error) {
      set({ operationStatus: 'error', operationError: getErrorMessage(error) });
      return null;
    }
  },
  startProject: async (projectId) => {
    set({ operationStatus: 'loading', operationError: null });
    try {
      const result = await startProjectApi(projectId);
      set((state) => ({
        operationStatus: 'success',
        detail:
          state.detail !== null && state.detail.id === projectId
            ? { ...state.detail, project_status: result.project_status }
            : state.detail,
      }));
      return true;
    } catch (error) {
      set({ operationStatus: 'error', operationError: getErrorMessage(error) });
      return false;
    }
  },
  stopProject: async (projectId) => {
    set({ operationStatus: 'loading', operationError: null });
    try {
      const result = await stopProjectApi(projectId);
      set((state) => ({
        operationStatus: 'success',
        detail:
          state.detail !== null && state.detail.id === projectId
            ? { ...state.detail, project_status: result.project_status }
            : state.detail,
      }));
      return true;
    } catch (error) {
      set({ operationStatus: 'error', operationError: getErrorMessage(error) });
      return false;
    }
  },
  deleteProject: async (projectId) => {
    set({ operationStatus: 'loading', operationError: null });
    try {
      await deleteProjectApi(projectId);
      set((state) => ({
        operationStatus: 'success',
        detail: state.detail !== null && state.detail.id === projectId ? null : state.detail,
      }));
      return true;
    } catch (error) {
      set({ operationStatus: 'error', operationError: getErrorMessage(error) });
      return false;
    }
  },
  resetDetail: () => set({ detail: null, detailStatus: 'idle', detailError: null }),
  resetOperationError: () => set({ operationError: null }),
}));
