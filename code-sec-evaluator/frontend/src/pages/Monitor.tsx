import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import { useParams } from 'react-router-dom';

import { getStages, getWorkers, listLogs, listResources } from '@/api/results';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/common/PageHeader';
import { LogStream } from '@/components/monitor/LogStream';
import { ResourceChart } from '@/components/monitor/ResourceChart';
import { StageStepper } from '@/components/monitor/StageStepper';
import { WorkerStatusList } from '@/components/monitor/WorkerStatusList';
import { useAsyncData } from '@/hooks/useAsyncData';
import { usePolling } from '@/hooks/usePolling';
import { useProjectStore } from '@/store/projectStore';

/** 实时监控页：REST 查询版（运行中每 5 秒刷新；WebSocket 实时推送在 M5 接入）。 */
export function Monitor() {
  const params = useParams();
  const projectId = Number(params.projectId);
  const detail = useProjectStore((state) => state.detail);
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

  return (
    <Box>
      <PageHeader
        title="实时监控"
        description="阶段 / 角色 / 日志 / 资源（运行中每 5 秒自动刷新）"
      />

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
        ) : stagesQuery.data === null || stagesQuery.data.length === 0 ? (
          <Typography color="text.secondary">暂无阶段记录。</Typography>
        ) : (
          <StageStepper stages={stagesQuery.data} />
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
              <WorkerStatusList items={workersQuery.data ?? []} />
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
              <LogStream logs={[...(logsQuery.data ?? [])].reverse()} />
            )}
          </Paper>
        </Grid>
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
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
                  <ResourceChart items={resourcesQuery.data ?? []} metric="cpu" />
                </Grid>
                <Grid item xs={12} md={4}>
                  <ResourceChart items={resourcesQuery.data ?? []} metric="memory" />
                </Grid>
                <Grid item xs={12} md={4}>
                  <ResourceChart items={resourcesQuery.data ?? []} metric="token" />
                </Grid>
              </Grid>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
