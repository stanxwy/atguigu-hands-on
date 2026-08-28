import DownloadOutlinedIcon from '@mui/icons-material/DownloadOutlined';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { formatDateTime } from '@/utils/format';

interface ReportViewerProps {
  markdown: string | null;
  html: string | null;
  createdAt: string | null;
  onDownload: () => void;
}

/** 报告查看器：HTML 沙箱预览。 */
export function ReportViewer({ markdown, html, createdAt, onDownload }: ReportViewerProps) {
  const hasHtml = html !== null && html !== '';

  return (
    <Box>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        sx={{ mb: 2, alignItems: { sm: 'center' }, justifyContent: 'space-between' }}
      >
        <Typography variant="caption" color="text.secondary">
          {createdAt !== null && `生成于 ${formatDateTime(createdAt)}`}
        </Typography>
        <Button variant="outlined" startIcon={<DownloadOutlinedIcon />} onClick={onDownload}>
          下载报告
        </Button>
      </Stack>

      {hasHtml ? (
        <iframe
          title="报告 HTML 预览"
          srcDoc={html}
          sandbox=""
          style={{
            width: '100%',
            height: 640,
            border: '1px solid rgba(0, 0, 0, 0.12)',
            borderRadius: 8,
          }}
        />
      ) : (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: 400,
            color: 'text.secondary',
            border: '1px dashed',
            borderColor: 'divider',
            borderRadius: 1,
          }}
        >
          <Typography>暂无 HTML 报告</Typography>
        </Box>
      )}
    </Box>
  );
}
