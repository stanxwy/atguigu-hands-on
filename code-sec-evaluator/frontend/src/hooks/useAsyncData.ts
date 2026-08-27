import { useCallback, useEffect, useRef, useState } from 'react';

import { getErrorMessage } from '@/api/client';
import type { AsyncStatus } from '@/types/api';

export interface AsyncDataResult<T> {
  data: T | null;
  status: AsyncStatus;
  error: string | null;
  reload: () => Promise<void>;
}

/**
 * 通用异步数据加载：key 变化时清空旧数据并重新加载；
 * reload 用于后台刷新（保留现有数据，避免轮询闪烁）。
 */
export function useAsyncData<T>(loader: () => Promise<T>, key: unknown): AsyncDataResult<T> {
  const loaderRef = useRef(loader);
  const dataRef = useRef<T | null>(null);
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<AsyncStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  loaderRef.current = loader;
  dataRef.current = data;

  const reload = useCallback(async () => {
    if (dataRef.current === null) {
      setStatus('loading');
    }
    setError(null);
    try {
      const result = await loaderRef.current();
      dataRef.current = result;
      setData(result);
      setStatus('success');
    } catch (err) {
      setError(getErrorMessage(err));
      setStatus('error');
    }
  }, []);

  useEffect(() => {
    setData(null);
    dataRef.current = null;
    void reload();
  }, [key, reload]);

  return { data, status, error, reload };
}
