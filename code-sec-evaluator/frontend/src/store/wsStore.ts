import { create } from 'zustand';

import { getAccessToken } from '@/api/client';
import { useProjectStore } from '@/store/projectStore';
import type {
  WsChatMessageData,
  WsEnvelope,
  WsResourceUsageData,
  WsRuntimeLogData,
  WsStageStatusData,
  WsVulnerabilityFoundData,
  WsWorkerStatusData,
} from '@/types/ws';

export type WsConnectionStatus = 'idle' | 'connecting' | 'open' | 'closed';

const MAX_BUFFER_SIZE = 200;
const HEARTBEAT_INTERVAL_MS = 25000;
const MAX_RECONNECT_DELAY_MS = 30000;
const WS_UNAUTHORIZED_CODE = 4001;

interface WsState {
  status: WsConnectionStatus;
  projectId: number | null;
  lastMessage: WsEnvelope | null;
  stageEvents: WsStageStatusData[];
  workerEvents: WsWorkerStatusData[];
  chatMessages: WsChatMessageData[];
  runtimeLogs: WsRuntimeLogData[];
  resourcePoints: WsResourceUsageData[];
  vulnEvents: WsVulnerabilityFoundData[];
  reportEvents: { reportId: number }[];
  connect: (projectId: number) => void;
  disconnect: () => void;
  clearBuffers: () => void;
  handleMessage: (envelope: WsEnvelope) => void;
}

let socket: WebSocket | null = null;
let heartbeatTimer: number | null = null;
let reconnectTimer: number | null = null;
let reconnectAttempts = 0;
let targetProjectId: number | null = null;

function clearHeartbeat(): void {
  if (heartbeatTimer !== null) {
    window.clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

function clearReconnect(): void {
  if (reconnectTimer !== null) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

function openSocket(projectId: number): void {
  const token = getAccessToken();
  if (token === null) {
    useWsStore.setState({ status: 'closed', projectId });
    return;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${protocol}://${window.location.host}/api/projects/${projectId}/stream?token=${encodeURIComponent(token)}`;
  useWsStore.setState({ status: 'connecting', projectId });

  const ws = new WebSocket(url);
  socket = ws;

  ws.onopen = () => {
    reconnectAttempts = 0;
    useWsStore.setState({ status: 'open' });
    heartbeatTimer = window.setInterval(() => {
      if (socket !== null && socket.readyState === WebSocket.OPEN) {
        socket.send('ping');
      }
    }, HEARTBEAT_INTERVAL_MS);
  };

  ws.onmessage = (event) => {
    if (typeof event.data !== 'string' || event.data === 'pong') {
      return;
    }
    try {
      const envelope = JSON.parse(event.data) as WsEnvelope;
      useWsStore.getState().handleMessage(envelope);
    } catch {
      // 忽略无法解析的消息
    }
  };

  ws.onerror = () => {
    // 连接错误由 onclose 统一触发重连
  };

  ws.onclose = (event) => {
    if (socket === ws) {
      socket = null;
    }
    clearHeartbeat();
    if (event.code === WS_UNAUTHORIZED_CODE || targetProjectId === null) {
      useWsStore.setState({ status: 'closed' });
      return;
    }
    useWsStore.setState({ status: 'connecting' });
    const delay = Math.min(1000 * 2 ** reconnectAttempts, MAX_RECONNECT_DELAY_MS);
    reconnectAttempts += 1;
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      if (targetProjectId !== null) {
        openSocket(targetProjectId);
      }
    }, delay);
  };
}

function closeSocket(): void {
  if (socket !== null) {
    socket.onopen = null;
    socket.onmessage = null;
    socket.onerror = null;
    socket.onclose = null;
    socket.close();
    socket = null;
  }
}

/**
 * WebSocket 状态：连接生命周期、心跳与指数退避重连集中在 store；
 * 8 种消息按类型写入有界缓冲区，供页面细粒度订阅。
 */
export const useWsStore = create<WsState>((set, get) => ({
  status: 'idle',
  projectId: null,
  lastMessage: null,
  stageEvents: [],
  workerEvents: [],
  chatMessages: [],
  runtimeLogs: [],
  resourcePoints: [],
  vulnEvents: [],
  reportEvents: [],
  connect: (projectId) => {
    const current = socket;
    if (
      targetProjectId === projectId &&
      current !== null &&
      (current.readyState === WebSocket.OPEN || current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }
    clearReconnect();
    clearHeartbeat();
    closeSocket();
    targetProjectId = projectId;
    reconnectAttempts = 0;
    get().clearBuffers();
    openSocket(projectId);
  },
  disconnect: () => {
    targetProjectId = null;
    reconnectAttempts = 0;
    clearReconnect();
    clearHeartbeat();
    closeSocket();
    set({ status: 'idle', projectId: null });
  },
  clearBuffers: () =>
    set({
      stageEvents: [],
      workerEvents: [],
      chatMessages: [],
      runtimeLogs: [],
      resourcePoints: [],
      vulnEvents: [],
      reportEvents: [],
    }),
  handleMessage: (envelope) => {
    switch (envelope.type) {
      case 'project_status':
        useProjectStore.setState((state) => ({
          detail:
            state.detail !== null && state.detail.id === envelope.project_id
              ? { ...state.detail, project_status: envelope.data.project_status }
              : state.detail,
        }));
        break;
      case 'stage_status':
        set((state) => ({
          stageEvents: [...state.stageEvents, envelope.data].slice(-MAX_BUFFER_SIZE),
        }));
        break;
      case 'worker_status':
        set((state) => ({
          workerEvents: [...state.workerEvents, envelope.data].slice(-MAX_BUFFER_SIZE),
        }));
        break;
      case 'chat_message':
        set((state) => ({
          chatMessages: [...state.chatMessages, envelope.data].slice(-MAX_BUFFER_SIZE),
        }));
        break;
      case 'runtime_log':
        set((state) => ({
          runtimeLogs: [
            ...state.runtimeLogs,
            { ...envelope.data, created_at: envelope.data.created_at ?? envelope.timestamp },
          ].slice(-MAX_BUFFER_SIZE),
        }));
        break;
      case 'resource_usage':
        set((state) => ({
          resourcePoints: [
            ...state.resourcePoints,
            { ...envelope.data, recorded_at: envelope.data.recorded_at ?? envelope.timestamp },
          ].slice(-MAX_BUFFER_SIZE),
        }));
        break;
      case 'vulnerability_found':
        set((state) => ({
          vulnEvents: [...state.vulnEvents, envelope.data].slice(-5),
        }));
        break;
      case 'report_ready':
        set((state) => ({
          reportEvents: [...state.reportEvents, { reportId: envelope.data.report_id }].slice(-5),
        }));
        break;
    }
    set({ lastMessage: envelope });
  },
}));
