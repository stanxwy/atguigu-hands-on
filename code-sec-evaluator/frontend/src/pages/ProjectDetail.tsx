import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Typography from '@mui/material/Typography';
import { useTheme } from '@mui/material/styles';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useCallback, useEffect, useState, type SyntheticEvent } from 'react';
import { Outlet, useLocation, useNavigate, useParams } from 'react-router-dom';

import { getErrorMessage } from '@/api/client';
import { getStages } from '@/api/results';
import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { LoadingState } from '@/components/common/LoadingState';
import { StatusTag } from '@/components/common/StatusTag';
import { StageStepper } from '@/components/monitor/StageStepper';
import { usePolling } from '@/hooks/usePolling';
import { useProjectStore } from '@/store/projectStore';
import type { AsyncStatus } from '@/types/api';
import type { StageItem } from '@/types/stage';
import { formatDateTime } from '@/utils/format';
import { REPORT_STATUS_LABELS, SOURCE_TYPE_LABELS } from '@/utils/labels';
import { isProjectStartable, isProjectStoppable } from '@/utils/projectStatus';

const DETAIL_TABS = [
  { label: '概览', path: '' },
  { label: '实时监控', path: 'monitor' },
  { label: '漏洞', path: 'vulnerabilities' },
  { label: '攻击路径', path: 'attack-paths' },
  { label: '报告', path: 'report' },
] as const;

type DetailDialogKind = 'start' | 'stop' | 'delete';

interface InfoCardProps {
  label: string;
  value: string;
}

function InfoCard({ label, value }: InfoCardProps) {
  return (
    <Paper sx={{ p: 2, height: '100%' }}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2" sx={{ mt: 0.5, wordBreak: 'break-all' }}>
        {value}
      </Typography>
    </Paper>
  );
}

/** 项目详情布局：共享头部（操作按钮 + 标签导航）+ 子路由内容。 */
export function ProjectDetail() {
  const params = useParams();
  const projectId = Number(params.projectId);
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'));

  const detail = useProjectStore((state) => state.detail);
  const detailStatus = useProjectStore((state) => state.detailStatus);
  const detailError = useProjectStore((state) => state.detailError);
  const fetchDetail = useProjectStore((state) => state.fetchDetail);
  const resetDetail = useProjectStore((state) => state.resetDetail);
  const startProject = useProjectStore((state) => state.startProject);
  const stopProject = useProjectStore((state) => state.stopProject);
  const deleteProject = useProjectStore((state) => state.deleteProject);
  const operationStatus = useProjectStore((state) => state.operationStatus);
  const operationError = useProjectStore((state) => state.operationError);

  const [dialog, setDialog] = useState<DetailDialogKind | null>(null);

  useEffect(() => {
    if (Number.isNaN(projectId)) {
      return;
    }
    resetDetail();
    void fetchDetail(projectId);
  }, [fetchDetail, projectId, resetDetail]);

  useEffect(
    () => () => {
      resetDetail();
    },
    [resetDetail],
  );

  const basePath = `/projects/${projectId}`;
  const activeTab =
    DETAIL_TABS.find((tab) =>
      tab.path === ''
        ? location.pathname === basePath
        : location.pathname.startsWith(`${basePath}/${tab.path}`),
    )?.path ?? '';

  const handleTabChange = (_event: SyntheticEvent, value: string) => {
    navigate(value === '' ? basePath : `${basePath}/${value}`);
  };

  const handleConfirm = async () => {
    if (dialog === null) {
      return;
    }
    let ok = false;
    if (dialog === 'start') {
      ok = await startProject(projectId);
    } else if (dialog === 'stop') {
      ok = await stopProject(projectId);
    } else {
      ok = await deleteProject(projectId);
    }
    setDialog(null);
    if (dialog === 'delete' && ok) {
      navigate('/projects');
    }
  };

  const dialogMeta =
    dialog === null
      ? null
      : {
          start: {
            title: '启动评估任务',
            description: `确定启动项目「${detail?.project_name ?? ''}」的评估任务吗？`,
            confirmText: '启动',
          },
          stop: {
            title: '停止评估任务',
            description: `确定停止项目「${detail?.project_name ?? ''}」的评估任务吗？已生成的数据会保留。`,
            confirmText: '停止',
          },
          delete: {
            title: '删除项目',
            description: `确定删除项目「${detail?.project_name ?? ''}」吗？该操作将级联删除漏洞、攻击路径、日志与文件，且不可恢复。`,
            confirmText: '删除',
          },
        }[dialog];

  if (detailStatus === 'loading' || detailStatus === 'idle') {
    return <LoadingState label="正在加载项目..." />;
  }
  if (detailStatus === 'error' || detail === null) {
    return (
      <Box>
        <ErrorAlert
          message={detailError ?? '项目加载失败'}
          onRetry={() => void fetchDetail(projectId)}
        />
        <Button onClick={() => navigate('/projects')}>返回项目列表</Button>
      </Box>
    );
  }

  return (
    <Box>
      <Stack
        direction={{ xs: 'column', lg: 'row' }}
        spacing={2}
        sx={{ mb: 2, alignItems: { lg: 'center' }, justifyContent: 'space-between' }}
      >
        <Box>
          <Typography variant="h5" component="h1">
            {detail.project_name}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1, alignItems: 'center' }}>
            <StatusTag variant="project" value={detail.project_status} />
            <Typography variant="body2" color="text.secondary">
              ID: {detail.id}
            </Typography>
          </Stack>
        </Box>
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
          {isProjectStartable(detail.project_status) && (
            <Button
              variant="contained"
              startIcon={<PlayArrowIcon />}
              onClick={() => setDialog('start')}
            >
              启动评估
            </Button>
          )}
          {isProjectStoppable(detail.project_status) && (
            <Button
              variant="outlined"
              color="warning"
              startIcon={<StopIcon />}
              onClick={() => setDialog('stop')}
            >
              停止任务
            </Button>
          )}
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteOutlineIcon />}
            disabled={detail.project_status === 'running'}
            onClick={() => setDialog('delete')}
          >
            删除项目
          </Button>
        </Stack>
      </Stack>

      {operationError !== null && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {operationError}
        </Alert>
      )}

      <Paper sx={{ px: 1, pt: 0.5 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          variant={isDesktop ? 'standard' : 'scrollable'}
          scrollButtons="auto"
        >
          {DETAIL_TABS.map((tab) => (
            <Tab key={tab.path} label={tab.label} value={tab.path} />
          ))}
        </Tabs>
      </Paper>
      <Divider />
      <Box sx={{ mt: 3 }}>
        <Outlet />
      </Box>

      {dialogMeta !== null && (
        <ConfirmDialog
          open
          title={dialogMeta.title}
          description={dialogMeta.description}
          confirmText={dialogMeta.confirmText}
          severity={dialog === 'delete' ? 'error' : 'warning'}
          loading={operationStatus === 'loading'}
          onConfirm={() => void handleConfirm()}
          onClose={() => setDialog(null)}
        />
      )}
    </Box>
  );
}

/** 项目概览：基本信息 + 统计 + 阶段状态（运行中每 5 秒刷新）。 */
export function ProjectOverview() {
  const detail = useProjectStore((state) => state.detail);
  const [stages, setStages] = useState<StageItem[]>([]);
  const [stagesStatus, setStagesStatus] = useState<AsyncStatus>('idle');
  const [stagesError, setStagesError] = useState<string | null>(null);

  const loadStages = useCallback(async (projectId: number) => {
    setStagesStatus('loading');
    try {
      const result = await getStages(projectId);
      setStages(result.list);
      setStagesStatus('success');
      setStagesError(null);
    } catch (error) {
      setStagesStatus('error');
      setStagesError(getErrorMessage(error));
    }
  }, []);

  useEffect(() => {
    if (detail === null) {
      return;
    }
    void loadStages(detail.id);
  }, [detail, loadStages]);

  usePolling(
    () => {
      if (detail !== null && detail.project_status === 'running') {
        void loadStages(detail.id);
      }
    },
    detail?.project_status === 'running' ? 5000 : null,
  );

  if (detail === null) {
    return <EmptyState title="项目不存在" />;
  }

  return (
    <Box>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={4}>
          <InfoCard label="源码来源" value={SOURCE_TYPE_LABELS[detail.source_type]} />
        </Grid>
        <Grid item xs={12} sm={6} md={8}>
          <InfoCard label="源码路径 / 仓库地址" value={detail.source_path} />
        </Grid>
        <Grid item xs={12} md={6}>
          <InfoCard label="任务说明" value={detail.task_content ?? '-'} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <InfoCard label="漏洞数量" value={`${detail.vuln_count}`} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <InfoCard label="攻击路径数量" value={`${detail.attack_path_count}`} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <InfoCard label="报告状态" value={REPORT_STATUS_LABELS[detail.report_status]} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <InfoCard label="更新时间" value={formatDateTime(detail.updated_at)} />
        </Grid>
      </Grid>

      <Paper sx={{ p: { xs: 2, md: 3 }, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          执行阶段
        </Typography>
        {stagesStatus === 'loading' || stagesStatus === 'idle' ? (
          <LoadingState label="正在加载阶段状态..." />
        ) : stagesStatus === 'error' ? (
          <ErrorAlert
            message={stagesError ?? '阶段状态加载失败'}
            onRetry={() => void loadStages(detail.id)}
          />
        ) : stages.length === 0 ? (
          <Typography color="text.secondary">项目尚未启动，暂无阶段记录。</Typography>
        ) : (
          <StageStepper stages={stages} />
        )}
      </Paper>
    </Box>
  );
}
