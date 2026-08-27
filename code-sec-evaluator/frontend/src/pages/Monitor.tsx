import { Box, Paper, Typography } from '@mui/material';

import { PageHeader } from '@/components/common/PageHeader';

/** 实时监控页（M5 里程碑实现完整功能，当前为占位）。 */
export function Monitor() {
  return (
    <Box>
      <PageHeader title="实时监控" description="阶段 / 角色 / 消息 / 日志 / 资源（实时）" />
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">实时监控将在 M5 里程碑实现。</Typography>
      </Paper>
    </Box>
  );
}
