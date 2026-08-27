import { Box, Paper, Typography } from '@mui/material';

import { PageHeader } from '@/components/common/PageHeader';

/** 项目列表页（M3 里程碑实现完整功能，当前为占位）。 */
export function ProjectList() {
  return (
    <Box>
      <PageHeader title="项目列表" description="项目生命周期管理" />
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">项目列表将在 M3 里程碑实现。</Typography>
      </Paper>
    </Box>
  );
}
