import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import ReportProblemOutlinedIcon from '@mui/icons-material/ReportProblemOutlined';
import WarningAmberOutlinedIcon from '@mui/icons-material/WarningAmberOutlined';
import Box from '@mui/material/Box';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import type { ReactNode } from 'react';

import type { MessageType } from '@/types/enums';
import type { WsChatMessageData } from '@/types/ws';
import { MESSAGE_TYPE_LABELS, WORKER_ROLE_LABELS } from '@/utils/labels';

interface ChatMessageListProps {
  messages: WsChatMessageData[];
}

const MESSAGE_ICON: Record<MessageType, ReactNode> = {
  info: <InfoOutlinedIcon fontSize="small" />,
  warning: <WarningAmberOutlinedIcon fontSize="small" />,
  error: <ErrorOutlineIcon fontSize="small" />,
  critical: <ReportProblemOutlinedIcon fontSize="small" />,
  success: <CheckCircleOutlineIcon fontSize="small" />,
};

const MESSAGE_COLOR: Record<MessageType, string> = {
  info: 'info.main',
  warning: 'warning.main',
  error: 'error.main',
  critical: 'error.main',
  success: 'success.main',
};

/** 角色消息流：按消息类型着色，最新消息在底部。 */
export function ChatMessageList({ messages }: ChatMessageListProps) {
  if (messages.length === 0) {
    return <Typography color="text.secondary">等待角色消息...</Typography>;
  }

  return (
    <Stack
      spacing={1}
      sx={{
        maxHeight: 420,
        overflow: 'auto',
        pr: 0.5,
      }}
    >
      {messages.map((message, index) => (
        <Box
          key={`${message.worker_role}-${index}`}
          sx={{
            display: 'flex',
            gap: 1,
            alignItems: 'flex-start',
            p: 1.5,
            borderRadius: 1,
            bgcolor: 'action.hover',
          }}
        >
          <Box sx={{ color: MESSAGE_COLOR[message.message_type], mt: 0.25 }}>
            {MESSAGE_ICON[message.message_type]}
          </Box>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="caption" color="text.secondary" fontWeight={600}>
              {WORKER_ROLE_LABELS[message.worker_role]} ·{' '}
              {MESSAGE_TYPE_LABELS[message.message_type]}
            </Typography>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {message.message_text}
            </Typography>
          </Box>
        </Box>
      ))}
    </Stack>
  );
}
