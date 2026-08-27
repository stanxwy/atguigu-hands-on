import { Box, Paper, Typography } from '@mui/material';

import { PageHeader } from '@/components/common/PageHeader';

/** 报告页（M4 里程碑实现完整功能，当前为占位）。 */
export function Report() {
  return (
    <Box>
      <PageHeader title="评估报告" description="预览与下载最终报告" />
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">报告将在 M4 里程碑实现。</Typography>
      </Paper>
    </Box>
  );
}
