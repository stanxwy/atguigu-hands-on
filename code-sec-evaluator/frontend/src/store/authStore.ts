import { create } from 'zustand';

import { initSystem as initSystemApi, login as loginApi } from '@/api/auth';
import { getAccessToken, getErrorMessage, setAccessToken } from '@/api/client';
import type { AsyncStatus } from '@/types/api';
import type { User } from '@/types/auth';

const USER_STORAGE_KEY = 'cse_user';

interface AuthState {
  user: User | null;
  status: AsyncStatus;
  error: string | null;
  isInitialized: boolean;
  init: () => void;
  login: (username: string, password: string) => Promise<boolean>;
  initSystem: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  resetError: () => void;
}

function readStoredUser(): User | null {
  const raw = window.localStorage.getItem(USER_STORAGE_KEY);
  if (raw === null) {
    return null;
  }
  try {
    return JSON.parse(raw) as User;
  } catch {
    window.localStorage.removeItem(USER_STORAGE_KEY);
    return null;
  }
}

function storeUser(user: User | null): void {
  if (user === null) {
    window.localStorage.removeItem(USER_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

/**
 * 认证状态：token 与用户信息持久化到 localStorage，
 * 登录/初始化/登出动作收敛于此，页面不散落请求逻辑。
 */
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: 'idle',
  error: null,
  isInitialized: false,
  init: () => {
    const token = getAccessToken();
    const user = token !== null ? readStoredUser() : null;
    set({ user, isInitialized: true });
  },
  login: async (username, password) => {
    set({ status: 'loading', error: null });
    try {
      const data = await loginApi({ username, password });
      setAccessToken(data.access_token);
      storeUser(data.user);
      set({ user: data.user, status: 'success', error: null });
      return true;
    } catch (error) {
      set({ status: 'error', error: getErrorMessage(error) });
      return false;
    }
  },
  initSystem: async (username, password) => {
    set({ status: 'loading', error: null });
    try {
      await initSystemApi({ username, password });
      set({ status: 'success', error: null });
      return true;
    } catch (error) {
      set({ status: 'error', error: getErrorMessage(error) });
      return false;
    }
  },
  logout: () => {
    setAccessToken(null);
    storeUser(null);
    set({ user: null, status: 'idle', error: null });
  },
  resetError: () => set({ error: null }),
}));
