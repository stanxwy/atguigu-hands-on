import { useEffect } from 'react';

import { useWsStore } from '@/store/wsStore';

/**
 * WebSocket 连接 hook：projectId 变化时切换订阅，卸载时断开。
 * 连接/心跳/重连逻辑收敛在 wsStore。
 */
export function useWebSocket(projectId: number): void {
  const connect = useWsStore((state) => state.connect);
  const disconnect = useWsStore((state) => state.disconnect);

  useEffect(() => {
    if (Number.isNaN(projectId)) {
      return undefined;
    }
    connect(projectId);
    return () => disconnect();
  }, [connect, disconnect, projectId]);
}
