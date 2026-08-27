import { useEffect, useRef } from 'react';

/**
 * 周期轮询：intervalMs 为 null 时停止；回调始终引用最新闭包。
 */
export function usePolling(callback: () => void, intervalMs: number | null): void {
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (intervalMs === null) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      callbackRef.current();
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [intervalMs]);
}
