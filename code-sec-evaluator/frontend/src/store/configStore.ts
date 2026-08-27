import { create } from 'zustand';

import { getErrorMessage } from '@/api/client';
import { getConfig as getConfigApi, updateConfig as updateConfigApi } from '@/api/system';
import type { AsyncStatus } from '@/types/api';
import type { ConfigUpdateResult, ConfigUpdates, SystemConfig } from '@/types/config';

interface ConfigState {
  config: SystemConfig | null;
  status: AsyncStatus;
  error: string | null;
  saving: boolean;
  saveError: string | null;
  fetchConfig: () => Promise<void>;
  updateConfig: (updates: ConfigUpdates) => Promise<boolean>;
  resetErrors: () => void;
}

/**
 * 系统配置状态：读取与更新收敛于此；
 * 更新成功后仅合并后端返回的变更分组。
 */
export const useConfigStore = create<ConfigState>((set) => ({
  config: null,
  status: 'idle',
  error: null,
  saving: false,
  saveError: null,
  fetchConfig: async () => {
    set({ status: 'loading', error: null });
    try {
      const config = await getConfigApi();
      set({ config, status: 'success' });
    } catch (error) {
      set({ status: 'error', error: getErrorMessage(error) });
    }
  },
  updateConfig: async (updates) => {
    set({ saving: true, saveError: null });
    try {
      const result: ConfigUpdateResult = await updateConfigApi(updates);
      set((state) => ({
        saving: false,
        config: state.config !== null ? { ...state.config, ...result } : state.config,
      }));
      return true;
    } catch (error) {
      set({ saving: false, saveError: getErrorMessage(error) });
      return false;
    }
  },
  resetErrors: () => set({ error: null, saveError: null }),
}));
