import { Box, Paper, Typography } from '@mui/material';

import { PageHeader } from '@/components/common/PageHeader';

/** 系统配置页（M6 里程碑实现完整功能，当前为占位）。 */
export function SystemConfig() {
  return (
    <Box>
      <PageHeader title="系统配置" description="隔离环境 / 任务 / 保留策略（管理员）" />
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">系统配置将在 M6 里程碑实现。</Typography>
      </Paper>
    </Box>
  );
}
