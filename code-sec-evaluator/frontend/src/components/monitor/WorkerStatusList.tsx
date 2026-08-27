import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { StatusTag } from '@/components/common/StatusTag';
import type { WorkerTaskItem } from '@/types/worker';
import { formatDateTime } from '@/utils/format';
import { STAGE_NAME_LABELS, WORKER_ROLE_LABELS } from '@/utils/labels';

interface WorkerStatusListProps {
  items: WorkerTaskItem[];
}

/** 角色执行状态列表：角色、阶段、状态与执行时间。 */
export function WorkerStatusList({ items }: WorkerStatusListProps) {
  if (items.length === 0) {
    return <Typography color="text.secondary">暂无角色任务记录。</Typography>;
  }

  return (
    <Stack spacing={1.5}>
      {items.map((item) => (
        <Box
          key={item.id}
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 1,
            alignItems: 'center',
            justifyContent: 'space-between',
            p: 1.5,
            borderRadius: 1,
            bgcolor: 'action.hover',
          }}
        >
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="body2" fontWeight={600}>
              {WORKER_ROLE_LABELS[item.worker_role]}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {item.stage_name !== null ? STAGE_NAME_LABELS[item.stage_name] : '-'} ·{' '}
              {formatDateTime(item.started_at)} ~ {formatDateTime(item.finished_at)}
            </Typography>
          </Box>
          <StatusTag variant="task" value={item.task_status} />
        </Box>
      ))}
    </Stack>
  );
}
