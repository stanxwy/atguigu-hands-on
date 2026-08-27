import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import IconButton from '@mui/material/IconButton';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Pagination from '@mui/material/Pagination';
import Paper from '@mui/material/Paper';
import Select, { type SelectChangeEvent } from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { ConfirmDialog } from '@/components/common/ConfirmDialog';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/common/PageHeader';
import { StatusTag } from '@/components/common/StatusTag';
import { ProjectTable } from '@/components/project/ProjectTable';
import { useProjectStore } from '@/store/projectStore';
import { PROJECT_STATUSES } from '@/types/enums';
import type { ProjectStatus } from '@/types/enums';
import type { ProjectListItem } from '@/types/project';
import { formatDateTime } from '@/utils/format';
import { PROJECT_STATUS_LABELS, SOURCE_TYPE_LABELS } from '@/utils/labels';
import { isProjectStartable, isProjectStoppable } from '@/utils/projectStatus';

const PAGE_SIZE = 10;

type DialogKind = 'start' | 'stop' | 'delete';

interface DialogState {
  kind: DialogKind;
  item: ProjectListItem;
}

/** 项目列表页：分页、状态筛选、启动/停止/删除（桌面表格 + 移动卡片）。 */
export function ProjectList() {
  const navigate = useNavigate();
  const list = useProjectStore((state) => state.list);
  const total = useProjectStore((state) => state.total);
  const listStatus = useProjectStore((state) => state.listStatus);
  const listError = useProjectStore((state) => state.listError);
  const fetchList = useProjectStore((state) => state.fetchList);
  const startProject = useProjectStore((state) => state.startProject);
  const stopProject = useProjectStore((state) => state.stopProject);
  const deleteProject = useProjectStore((state) => state.deleteProject);
  const operationStatus = useProjectStore((state) => state.operationStatus);

  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<ProjectStatus | ''>('');
  const [dialog, setDialog] = useState<DialogState | null>(null);

  const currentParams = { page, page_size: PAGE_SIZE, project_status: statusFilter };

  useEffect(() => {
    void fetchList({ page, page_size: PAGE_SIZE, project_status: statusFilter });
  }, [fetchList, page, statusFilter]);

  const handleStatusFilterChange = (event: SelectChangeEvent<ProjectStatus | ''>) => {
    setStatusFilter(event.target.value as ProjectStatus | '');
    setPage(1);
  };

  const handleConfirm = async () => {
    if (dialog === null) {
      return;
    }
    const { kind, item } = dialog;
    if (kind === 'start') {
      await startProject(item.id);
    } else if (kind === 'stop') {
      await stopProject(item.id);
    } else {
      await deleteProject(item.id);
    }
    setDialog(null);
    if (kind === 'delete' && list.length === 1 && page > 1) {
      setPage(page - 1);
      return;
    }
    await fetchList(currentParams);
  };

  const dialogMeta =
    dialog === null
      ? null
      : {
          start: {
            title: '启动评估任务',
            description: `确定启动项目「${dialog.item.project_name}」的评估任务吗？`,
            confirmText: '启动',
          },
          stop: {
            title: '停止评估任务',
            description: `确定停止项目「${dialog.item.project_name}」的评估任务吗？已生成的数据会保留。`,
            confirmText: '停止',
          },
          delete: {
            title: '删除项目',
            description: `确定删除项目「${dialog.item.project_name}」吗？该操作将级联删除漏洞、攻击路径、日志与文件，且不可恢复。`,
            confirmText: '删除',
          },
        }[dialog.kind];

  const actionButtons = (item: ProjectListItem) => (
    <Stack direction="row" spacing={0.5} justifyContent="flex-end">
      <Tooltip title="查看详情">
        <span>
          <IconButton size="small" onClick={() => navigate(`/projects/${item.id}`)}>
            <VisibilityOutlinedIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
      {isProjectStartable(item.project_status) && (
        <Tooltip title="启动评估">
          <span>
            <IconButton
              size="small"
              color="primary"
              onClick={() => setDialog({ kind: 'start', item })}
            >
              <PlayArrowIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      )}
      {isProjectStoppable(item.project_status) && (
        <Tooltip title="停止任务">
          <span>
            <IconButton
              size="small"
              color="warning"
              onClick={() => setDialog({ kind: 'stop', item })}
            >
              <StopIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
      )}
      <Tooltip title="删除项目">
        <span>
          <IconButton
            size="small"
            color="error"
            disabled={item.project_status === 'running'}
            onClick={() => setDialog({ kind: 'delete', item })}
          >
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
    </Stack>
  );

  return (
    <Box>
      <PageHeader title="项目列表" description="创建、启动、停止与删除评估项目" />

      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        sx={{ mb: 2, alignItems: { sm: 'center' }, justifyContent: 'space-between' }}
      >
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel id="project-status-filter-label">项目状态</InputLabel>
          <Select
            labelId="project-status-filter-label"
            label="项目状态"
            value={statusFilter}
            onChange={handleStatusFilterChange}
          >
            <MenuItem value="">全部状态</MenuItem>
            {PROJECT_STATUSES.map((status) => (
              <MenuItem key={status} value={status}>
                {PROJECT_STATUS_LABELS[status]}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/projects/new')}
        >
          新建项目
        </Button>
      </Stack>

      {listStatus === 'loading' && <LoadingState label="正在加载项目..." />}
      {listStatus === 'error' && (
        <ErrorAlert
          message={listError ?? '项目列表加载失败'}
          onRetry={() => void fetchList(currentParams)}
        />
      )}
      {listStatus === 'success' &&
        (list.length === 0 ? (
          <EmptyState title="暂无项目" description="点击「新建项目」接入第一个评估项目。" />
        ) : (
          <>
            <Box sx={{ display: { xs: 'none', md: 'block' } }}>
              <Paper>
                <ProjectTable
                  items={list}
                  onView={(projectId) => navigate(`/projects/${projectId}`)}
                  onStart={(item) => setDialog({ kind: 'start', item })}
                  onStop={(item) => setDialog({ kind: 'stop', item })}
                  onDelete={(item) => setDialog({ kind: 'delete', item })}
                />
              </Paper>
            </Box>
            <Stack spacing={1.5} sx={{ display: { xs: 'flex', md: 'none' } }}>
              {list.map((item) => (
                <Paper key={item.id} sx={{ p: 2 }}>
                  <Stack
                    direction="row"
                    spacing={1}
                    sx={{ alignItems: 'center', justifyContent: 'space-between', mb: 1 }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="subtitle1" noWrap>
                        {item.project_name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {SOURCE_TYPE_LABELS[item.source_type]}
                      </Typography>
                    </Box>
                    <StatusTag variant="project" value={item.project_status} />
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    最近启动：{formatDateTime(item.last_started_at)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    最近完成：{formatDateTime(item.last_finished_at)}
                  </Typography>
                  {actionButtons(item)}
                </Paper>
              ))}
            </Stack>
            <Stack direction="row" sx={{ justifyContent: 'flex-end', mt: 2 }}>
              <Pagination
                count={Math.max(1, Math.ceil(total / PAGE_SIZE))}
                page={page}
                onChange={(_event, value) => setPage(value)}
                color="primary"
              />
            </Stack>
          </>
        ))}

      {dialogMeta !== null && (
        <ConfirmDialog
          open
          title={dialogMeta.title}
          description={dialogMeta.description}
          confirmText={dialogMeta.confirmText}
          severity={dialog?.kind === 'delete' ? 'error' : 'warning'}
          loading={operationStatus === 'loading'}
          onConfirm={() => void handleConfirm()}
          onClose={() => setDialog(null)}
        />
      )}
    </Box>
  );
}
