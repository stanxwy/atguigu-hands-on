import type { InitData, InitRequest, LoginData, LoginRequest } from '@/types/auth';

import { request } from './client';

/** 初始化管理员账户（仅未初始化时可调用）。 */
export function initSystem(payload: InitRequest): Promise<InitData> {
  return request<InitData>({ url: '/system/init', method: 'post', data: payload });
}

/** 登录并获取 JWT 与用户信息。 */
export function login(payload: LoginRequest): Promise<LoginData> {
  return request<LoginData>({ url: '/system/login', method: 'post', data: payload });
}
