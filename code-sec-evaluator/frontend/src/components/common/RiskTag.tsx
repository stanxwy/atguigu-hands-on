import Chip from '@mui/material/Chip';

import type { RiskLevel } from '@/types/enums';
import { RISK_LEVEL_LABELS } from '@/utils/labels';

interface RiskTagProps {
  level: RiskLevel;
  size?: 'small' | 'medium';
}

const RISK_BG_COLOR: Record<RiskLevel, string> = {
  critical: '#b91c1c',
  high: '#ea580c',
  medium: '#f59e0b',
  low: '#3b82f6',
};

/** 风险等级标签：严重/高危/中危/低危（深色底白字）。 */
export function RiskTag({ level, size = 'small' }: RiskTagProps) {
  return (
    <Chip
      label={RISK_LEVEL_LABELS[level]}
      size={size}
      sx={{ bgcolor: RISK_BG_COLOR[level], color: '#ffffff', fontWeight: 600 }}
    />
  );
}
