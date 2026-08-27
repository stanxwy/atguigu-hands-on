import { Box, Typography } from '@mui/material';

interface PageHeaderProps {
  title: string;
  description?: string;
}

/** 页面标题区：标题 + 可选描述。 */
export function PageHeader({ title, description }: PageHeaderProps) {
  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h5" component="h1" gutterBottom>
        {title}
      </Typography>
      {description !== undefined && (
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>
      )}
    </Box>
  );
}
