import axios, {
  isAxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
} from 'axios';

import type { ApiResponse } from '@/types/api';

const TOKEN_STORAGE_KEY = 'cse_access_token';

/** 登录态失效事件：拦截器触发，authStore 监听后清理并跳转登录页。 */
export const AUTH_UNAUTHORIZED_EVENT = 'cse:auth-unauthorized';

/** 业务错误：携带后端统一响应中的业务码（code）。 */
export class ApiBusinessError extends Error {
  readonly code: number;

  constructor(code: number, message: string) {
    super(message);
    this.name = 'ApiBusinessError';
    this.code = code;
  }
}

function isApiResponse(value: unknown): value is ApiResponse<unknown> {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as ApiResponse<unknown>).code === 'number'
  );
}

function emitUnauthorized(): void {
  window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT));
}

export function getAccessToken(): string | null {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setAccessToken(token: string | null): void {
  if (token === null) {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    return;
  }
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

/**
 * 统一 Axios 实例：注入 Bearer token、解包统一响应、统一错误处理。
 */
export const client: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 20000,
});

client.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token !== null) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response: AxiosResponse<unknown>) => {
    const payload = response.data;
    if (isApiResponse(payload) && payload.code !== 0) {
      if (payload.code === 1002) {
        emitUnauthorized();
      }
      return Promise.reject(new ApiBusinessError(payload.code, payload.message));
    }
    return response;
  },
  (error: unknown) => {
    if (isAxiosError<ApiResponse<unknown>>(error)) {
      const httpStatus = error.response?.status;
      const payload = error.response?.data;
      const code = payload?.code ?? 0;
      if (httpStatus === 401 || code === 1002) {
        emitUnauthorized();
      }
      return Promise.reject(
        new ApiBusinessError(code, payload?.message ?? error.message ?? '网络请求失败'),
      );
    }
    return Promise.reject(new ApiBusinessError(0, '网络请求失败'));
  },
);

/**
 * 通用请求封装：直接返回统一响应体中的 data 字段。
 */
export async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await client.request<ApiResponse<T>>(config);
  return response.data.data;
}
