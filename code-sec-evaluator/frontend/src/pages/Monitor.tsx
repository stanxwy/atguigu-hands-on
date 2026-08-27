import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';

import { getStages, getWorkers, listLogs, listResources } from '@/api/results';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/common/PageHeader';
import { ChatMessageList } from '@/components/monitor/ChatMessageList';
import { LogStream } from '@/components/monitor/LogStream';
import { ResourceChart } from '@/components/monitor/ResourceChart';
import { StageStepper } from '@/components/monitor/StageStepper';
import { WorkerStatusList } from '@/components/monitor/WorkerStatusList';
import { useAsyncData } from '@/hooks/useAsyncData';
import { usePolling } from '@/hooks/usePolling';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useProjectStore } from '@/store/projectStore';
import { useWsStore, type WsConnectionStatus } from '@/store/wsStore';
import type { RuntimeLogItem } from '@/types/log';
import type { ResourceUsageItem } from '@/types/resource';
import type { StageItem } from '@/types/stage';
import type { WorkerTaskItem } from '@/types/worker';
import { RISK_LEVEL_LABELS } from '@/utils/labels';
import { mergeStageEvents, mergeWorkerEvents } from '@/utils/wsMerge';

const MAX_LOCAL_LOGS = 300;
const MAX_LOCAL_RESOURCES = 60;

let syntheticId = 0;

const WS_STATUS_META: Record<
  WsConnectionStatus,
  { label: string; color: 'default' | 'success' | 'warning' }
> = {
  idle: { label: '未连接', color: 'default' },
  connecting: { label: '连接中...', color: 'warning' },
  open: { label: '实时连接已建立', color: 'success' },
  closed: { label: '连接已断开', color: 'default' },
};

/** 实时监控页：REST 首屏 + WebSocket 实时增量（心跳、断线指数退避重连）。 */
export function Monitor() {
  const params = useParams();
  const projectId = Number(params.projectId);
  const detail = useProjectStore((state) => state.detail);
  const wsStatus = useWsStore((state) => state.status);
  const stageEvents = useWsStore((state) => state.stageEvents);
  const workerEvents = useWsStore((state) => state.workerEvents);
  const wsLogs = useWsStore((state) => state.runtimeLogs);
  const wsResources = useWsStore((state) => state.resourcePoints);
  const chatMessages = useWsStore((state) => state.chatMessages);
  const vulnEvents = useWsStore((state) => state.vulnEvents);
  const reportEvents = useWsStore((state) => state.reportEvents);

  useWebSocket(projectId);

  const stagesQuery = useAsyncData(
    () => getStages(projectId).then((result) => result.list),
    projectId,
  );
  const workersQuery = useAsyncData(
    () => getWorkers(projectId).then((result) => result.list),
    projectId,
  );
  const logsQuery = useAsyncData(
    () => listLogs(projectId, { page: 1, page_size: 100 }).then((result) => result.list),
    projectId,
  );
  const resourcesQuery = useAsyncData(
    () => listResources(projectId, 60).then((result) => result.list),
    projectId,
  );

  const [stages, setStages] = useState<StageItem[]>([]);
  const [workers, setWorkers] = useState<WorkerTaskItem[]>([]);
  const [logs, setLogs] = useState<RuntimeLogItem[]>([]);
  const [resources, setResources] = useState<ResourceUsageItem[]>([]);
  const processedLogCount = useRef(0);
  const processedResourceCount = useRef(0);

  useEffect(() => {
    processedLogCount.current = 0;
    processedResourceCount.current = 0;
  }, [projectId]);

  useEffect(() => {
    if (stagesQuery.status === 'success' && stagesQuery.data !== null) {
      setStages(stagesQuery.data);
    }
  }, [stagesQuery.data, stagesQuery.status]);

  useEffect(() => {
    if (workersQuery.status === 'success' && workersQuery.data !== null) {
      setWorkers(workersQuery.data);
    }
  }, [workersQuery.data, workersQuery.status]);

  useEffect(() => {
    if (logsQuery.status === 'success' && logsQuery.data !== null) {
      setLogs(logsQuery.data);
    }
  }, [logsQuery.data, logsQuery.status]);

  useEffect(() => {
    if (resourcesQuery.status === 'success' && resourcesQuery.data !== null) {
      setResources(resourcesQuery.data);
    }
  }, [resourcesQuery.data, resourcesQuery.status]);

  useEffect(() => {
    if (stageEvents.length === 0) {
      return;
    }
    setStages((prev) => mergeStageEvents(prev, stageEvents));
  }, [stageEvents]);

  useEffect(() => {
    if (workerEvents.length === 0) {
      return;
    }
    setWorkers((prev) => mergeWorkerEvents(prev, workerEvents));
  }, [workerEvents]);

  useEffect(() => {
    if (wsLogs.length <= processedLogCount.current) {
      return;
    }
    const freshLogs = wsLogs.slice(processedLogCount.current);
    processedLogCount.current = wsLogs.length;
    setLogs((prev) => {
      const additions = freshLogs.map((log) => ({
        id: --syntheticId,
        log_level: log.log_level,
        log_content: log.log_content,
        stage_name: null,
        created_at: new Date().toISOString(),
      }));
      return [...prev, ...additions].slice(-MAX_LOCAL_LOGS);
    });
  }, [wsLogs]);

  useEffect(() => {
    if (wsResources.length <= processedResourceCount.current) {
      return;
    }
    const freshResources = wsResources.slice(processedResourceCount.current);
    processedResourceCount.current = wsResources.length;
    setResources((prev) => {
      const additions = freshResources.map((point) => ({
        cpu_usage: point.cpu_usage,
        memory_usage: point.memory_usage,
        token_count: point.token_count,
        recorded_at: new Date().toISOString(),
      }));
      return [...prev, ...additions].slice(-MAX_LOCAL_RESOURCES);
    });
  }, [wsResources]);

  usePolling(
    () => {
      if (detail?.project_status !== 'running') {
        return;
      }
      void stagesQuery.reload();
      void workersQuery.reload();
      void logsQuery.reload();
      void resourcesQuery.reload();
    },
    detail?.project_status === 'running' ? 5000 : null,
  );

  const terminalStatus = detail?.project_status ?? null;
  const previousStatus = useRef(terminalStatus);
  useEffect(() => {
    const current = terminalStatus;
    const previous = previousStatus.current;
    previousStatus.current = current;
    if (
      current !== null &&
      current !== previous &&
      (current === 'completed' || current === 'failed' || current === 'stopped')
    ) {
      void stagesQuery.reload();
      void workersQuery.reload();
      void logsQuery.reload();
      void resourcesQuery.reload();
    }
  }, [logsQuery, resourcesQuery, stagesQuery, terminalStatus, workersQuery]);

  const wsMeta = WS_STATUS_META[wsStatus];

  return (
    <Box>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        sx={{ alignItems: { sm: 'center' }, justifyContent: 'space-between' }}
      >
        <PageHeader
          title="实时监控"
          description="阶段 / 角色 / 消息 / 日志 / 资源（WebSocket 实时推送）"
        />
        <Chip label={wsMeta.label} color={wsMeta.color} size="small" sx={{ mb: 3 }} />
      </Stack>

      {vulnEvents.length > 0 &&
        vulnEvents
          .slice(-3)
          .reverse()
          .map((event, index) => (
            <Alert
              key={`vuln-${index}`}
              severity={
                event.risk_level === 'critical' || event.risk_level === 'high' ? 'error' : 'warning'
              }
              sx={{ mb: 1 }}
            >
              新漏洞发现：{event.vuln_title}（{RISK_LEVEL_LABELS[event.risk_level]}）
            </Alert>
          ))}
      {reportEvents.length > 0 && (
        <Alert severity="success" sx={{ mb: 1 }}>
          报告已生成（ID: {reportEvents[reportEvents.length - 1].reportId}），可前往「报告」页查看。
        </Alert>
      )}

      <Paper sx={{ p: { xs: 2, md: 3 }, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          执行阶段
        </Typography>
        {stagesQuery.status === 'loading' || stagesQuery.status === 'idle' ? (
          <LoadingState label="正在加载阶段状态..." />
        ) : stagesQuery.status === 'error' ? (
          <ErrorAlert
            message={stagesQuery.error ?? '阶段状态加载失败'}
            onRetry={() => void stagesQuery.reload()}
          />
        ) : stages.length === 0 ? (
          <Typography color="text.secondary">暂无阶段记录。</Typography>
        ) : (
          <StageStepper stages={stages} />
        )}
      </Paper>

      <Grid container spacing={2}>
        <Grid item xs={12} lg={5}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              角色执行状态
            </Typography>
            {workersQuery.status === 'loading' || workersQuery.status === 'idle' ? (
              <LoadingState label="正在加载角色状态..." />
            ) : workersQuery.status === 'error' ? (
              <ErrorAlert
                message={workersQuery.error ?? '角色状态加载失败'}
                onRetry={() => void workersQuery.reload()}
              />
            ) : (
              <WorkerStatusList items={workers} />
            )}
          </Paper>
        </Grid>
        <Grid item xs={12} lg={7}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              运行日志
            </Typography>
            {logsQuery.status === 'loading' || logsQuery.status === 'idle' ? (
              <LoadingState label="正在加载日志..." />
            ) : logsQuery.status === 'error' ? (
              <ErrorAlert
                message={logsQuery.error ?? '日志加载失败'}
                onRetry={() => void logsQuery.reload()}
              />
            ) : (
              <LogStream logs={[...logs].reverse()} />
            )}
          </Paper>
        </Grid>
        <Grid item xs={12} lg={5}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              角色消息
            </Typography>
            <ChatMessageList messages={chatMessages} />
          </Paper>
        </Grid>
        <Grid item xs={12} lg={7}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              资源消耗
            </Typography>
            {resourcesQuery.status === 'loading' || resourcesQuery.status === 'idle' ? (
              <LoadingState label="正在加载资源数据..." />
            ) : resourcesQuery.status === 'error' ? (
              <ErrorAlert
                message={resourcesQuery.error ?? '资源数据加载失败'}
                onRetry={() => void resourcesQuery.reload()}
              />
            ) : (
              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <ResourceChart items={resources} metric="cpu" />
                </Grid>
                <Grid item xs={12} md={4}>
                  <ResourceChart items={resources} metric="memory" />
                </Grid>
                <Grid item xs={12} md={4}>
                  <ResourceChart items={resources} metric="token" />
                </Grid>
              </Grid>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
