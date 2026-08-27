import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import IconButton from '@mui/material/IconButton';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';

import { StatusTag } from '@/components/common/StatusTag';
import type { ProjectListItem } from '@/types/project';
import { formatDateTime } from '@/utils/format';
import { SOURCE_TYPE_LABELS } from '@/utils/labels';
import { isProjectStartable, isProjectStoppable } from '@/utils/projectStatus';

interface ProjectTableProps {
  items: ProjectListItem[];
  onView: (projectId: number) => void;
  onStart: (item: ProjectListItem) => void;
  onStop: (item: ProjectListItem) => void;
  onDelete: (item: ProjectListItem) => void;
}

/** 项目列表表格（桌面端）。 */
export function ProjectTable({ items, onView, onStart, onStop, onDelete }: ProjectTableProps) {
  return (
    <TableContainer>
      <Table size="medium">
        <TableHead>
          <TableRow>
            <TableCell>项目名称</TableCell>
            <TableCell>源码来源</TableCell>
            <TableCell>状态</TableCell>
            <TableCell>最近启动</TableCell>
            <TableCell>最近完成</TableCell>
            <TableCell align="right">操作</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.id} hover>
              <TableCell>
                <Typography variant="body2" fontWeight={600}>
                  {item.project_name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  ID: {item.id}
                </Typography>
              </TableCell>
              <TableCell>{SOURCE_TYPE_LABELS[item.source_type]}</TableCell>
              <TableCell>
                <StatusTag variant="project" value={item.project_status} />
              </TableCell>
              <TableCell>{formatDateTime(item.last_started_at)}</TableCell>
              <TableCell>{formatDateTime(item.last_finished_at)}</TableCell>
              <TableCell align="right">
                <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                  <Tooltip title="查看详情">
                    <span>
                      <IconButton size="small" onClick={() => onView(item.id)}>
                        <VisibilityOutlinedIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                  {isProjectStartable(item.project_status) && (
                    <Tooltip title="启动评估">
                      <span>
                        <IconButton size="small" color="primary" onClick={() => onStart(item)}>
                          <PlayArrowIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  )}
                  {isProjectStoppable(item.project_status) && (
                    <Tooltip title="停止任务">
                      <span>
                        <IconButton size="small" color="warning" onClick={() => onStop(item)}>
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
                        onClick={() => onDelete(item)}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                </Stack>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
