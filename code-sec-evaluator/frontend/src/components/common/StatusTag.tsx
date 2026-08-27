import Chip, { type ChipProps } from '@mui/material/Chip';

import type { ProjectStatus, StageStatus, TaskStatus, VerifyStatus } from '@/types/enums';
import {
  PROJECT_STATUS_LABELS,
  STAGE_STATUS_LABELS,
  TASK_STATUS_LABELS,
  VERIFY_STATUS_LABELS,
} from '@/utils/labels';

type StatusVariant = 'project' | 'stage' | 'task' | 'verify';
type TagColor = NonNullable<ChipProps['color']>;

interface StatusTagProps {
  variant: StatusVariant;
  value: ProjectStatus | StageStatus | TaskStatus | VerifyStatus;
  size?: 'small' | 'medium';
}

const COLOR_MAP: Record<StatusVariant, Record<string, TagColor>> = {
  project: {
    created: 'default',
    running: 'primary',
    completed: 'success',
    failed: 'error',
    stopped: 'warning',
  },
  stage: {
    pending: 'default',
    running: 'primary',
    success: 'success',
    failed: 'error',
  },
  task: {
    idle: 'default',
    running: 'primary',
    success: 'success',
    failed: 'error',
  },
  verify: {
    unverified: 'default',
    verifying: 'primary',
    verified: 'success',
    failed: 'error',
  },
};

const LABEL_MAP: Record<StatusVariant, Record<string, string>> = {
  project: PROJECT_STATUS_LABELS,
  stage: STAGE_STATUS_LABELS,
  task: TASK_STATUS_LABELS,
  verify: VERIFY_STATUS_LABELS,
};

/** 状态标签：按类型与枚举值渲染颜色与中文文案。 */
export function StatusTag({ variant, value, size = 'small' }: StatusTagProps) {
  return (
    <Chip
      label={LABEL_MAP[variant][value] ?? value}
      color={COLOR_MAP[variant][value] ?? 'default'}
      size={size}
    />
  );
}
