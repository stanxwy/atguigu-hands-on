import DownloadOutlinedIcon from '@mui/icons-material/DownloadOutlined';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Typography from '@mui/material/Typography';
import { useState, type MouseEvent } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';

import { formatDateTime } from '@/utils/format';

type ViewMode = 'preview' | 'html';

interface ReportViewerProps {
  markdown: string | null;
  html: string | null;
  createdAt: string | null;
  onDownload: () => void;
}

/** 报告查看器：Markdown 安全渲染（react-markdown + rehype-sanitize）与 HTML 沙箱预览。 */
export function ReportViewer({ markdown, html, createdAt, onDownload }: ReportViewerProps) {
  const [mode, setMode] = useState<ViewMode>('preview');
  const hasHtml = html !== null && html !== '';

  const handleModeChange = (_event: MouseEvent<HTMLElement>, nextMode: ViewMode | null) => {
    if (nextMode !== null) {
      setMode(nextMode);
    }
  };

  return (
    <Box>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={2}
        sx={{ mb: 2, alignItems: { sm: 'center' }, justifyContent: 'space-between' }}
      >
        <Stack direction="row" spacing={2} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
          <ToggleButtonGroup exclusive size="small" value={mode} onChange={handleModeChange}>
            <ToggleButton value="preview">Markdown 预览</ToggleButton>
            {hasHtml && <ToggleButton value="html">HTML 预览</ToggleButton>}
          </ToggleButtonGroup>
          {createdAt !== null && (
            <Typography variant="caption" color="text.secondary">
              生成于 {formatDateTime(createdAt)}
            </Typography>
          )}
        </Stack>
        <Button variant="outlined" startIcon={<DownloadOutlinedIcon />} onClick={onDownload}>
          下载报告
        </Button>
      </Stack>

      {mode === 'preview' ? (
        <Box
          sx={{
            '& h1, & h2, & h3, & h4': { mt: 3, mb: 1.5 },
            '& p': { my: 1 },
            '& table': { borderCollapse: 'collapse', width: '100%', my: 2 },
            '& th, & td': { border: '1px solid', borderColor: 'divider', p: 1 },
            '& pre': {
              bgcolor: 'grey.100',
              p: 2,
              borderRadius: 1,
              overflow: 'auto',
              fontSize: 13,
            },
            '& code': { fontFamily: 'Consolas, Menlo, monospace' },
            '& blockquote': {
              borderLeft: '4px solid',
              borderColor: 'divider',
              pl: 2,
              color: 'text.secondary',
              my: 2,
            },
            wordBreak: 'break-word',
          }}
        >
          <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{markdown ?? ''}</ReactMarkdown>
        </Box>
      ) : (
        <iframe
          title="报告 HTML 预览"
          srcDoc={html ?? ''}
          sandbox=""
          style={{
            width: '100%',
            height: 640,
            border: '1px solid rgba(0, 0, 0, 0.12)',
            borderRadius: 8,
          }}
        />
      )}
    </Box>
  );
}
