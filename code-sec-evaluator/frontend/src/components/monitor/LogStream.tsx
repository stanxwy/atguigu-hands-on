import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { useEffect, useRef } from 'react';

import type { LogLevel } from '@/types/enums';
import type { RuntimeLogItem } from '@/types/log';
import { formatDateTime } from '@/utils/format';

const LOG_COLOR: Record<LogLevel, string> = {
  debug: 'text.secondary',
  info: 'text.primary',
  warn: 'warning.main',
  error: 'error.main',
};

interface LogStreamProps {
  logs: RuntimeLogItem[];
  autoScroll?: boolean;
}

/** 日志滚动流：等宽字体 + 按级别着色，默认自动滚动到底部。 */
export function LogStream({ logs, autoScroll = true }: LogStreamProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (autoScroll && containerRef.current !== null) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [autoScroll, logs]);

  if (logs.length === 0) {
    return <Typography color="text.secondary">暂无日志。</Typography>;
  }

  return (
    <Box
      ref={containerRef}
      sx={{
        maxHeight: 420,
        overflow: 'auto',
        fontFamily: 'Consolas, Menlo, monospace',
        fontSize: 13,
        lineHeight: 1.7,
        bgcolor: 'grey.900',
        color: 'grey.100',
        borderRadius: 1,
        p: 1.5,
      }}
    >
      {logs.map((log) => (
        <Box key={log.id} component="div" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          <Box component="span" sx={{ color: 'grey.500' }}>
            [{formatDateTime(log.created_at)}]
          </Box>{' '}
          <Box component="span" sx={{ color: LOG_COLOR[log.log_level] }}>
            [{log.log_level.toUpperCase()}]
          </Box>{' '}
          {log.log_content}
        </Box>
      ))}
    </Box>
  );
}
