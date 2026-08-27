import { Box, Typography } from '@mui/material';

/**
 * 应用根组件（M1 占位）。
 *
 * 路由、布局与页面将在 M2 起逐步接入；
 * 当前仅验证工程初始化、主题与构建链路。
 */
export function App() {
  return (
    <Box sx={{ p: 4 }}>
      <Typography variant="h4" gutterBottom>
        自动化安全评估系统
      </Typography>
      <Typography variant="body1" color="text.secondary">
        前端工程已就绪（M1 工程初始化）。
      </Typography>
    </Box>
  );
}
