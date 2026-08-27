import { Box, Paper, Typography } from '@mui/material';

import { PageHeader } from '@/components/common/PageHeader';

/** 攻击路径列表页（M4 里程碑实现完整功能，当前为占位）。 */
export function AttackPathList() {
  return (
    <Box>
      <PageHeader title="攻击路径" description="关联漏洞与利用顺序" />
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <Typography color="text.secondary">攻击路径将在 M4 里程碑实现。</Typography>
      </Paper>
    </Box>
  );
}
