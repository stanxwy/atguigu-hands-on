import { Box, CircularProgress, Typography } from '@mui/material';

interface LoadingStateProps {
  label?: string;
}

/** 通用加载态（居中转圈 + 提示文案）。 */
export function LoadingState({ label = '加载中...' }: LoadingStateProps) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
        py: 8,
      }}
    >
      <CircularProgress />
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}
