/**
 * 统一响应封装与通用类型（对齐 API 接口文档 §3 与后端 core/errors.py）。
 */

export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

/** 列表接口统一返回 data.list + data.total。 */
export interface Paginated<T> {
  list: T[];
  total: number;
}

/** 通用异步状态。 */
export type AsyncStatus = 'idle' | 'loading' | 'success' | 'error';
