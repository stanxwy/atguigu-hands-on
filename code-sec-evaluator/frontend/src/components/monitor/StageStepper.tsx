import Box from '@mui/material/Box';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import Stepper from '@mui/material/Stepper';
import Typography from '@mui/material/Typography';
import { useTheme } from '@mui/material/styles';
import useMediaQuery from '@mui/material/useMediaQuery';

import { StatusTag } from '@/components/common/StatusTag';
import type { StageItem } from '@/types/stage';
import { formatDateTime } from '@/utils/format';
import { STAGE_NAME_LABELS } from '@/utils/labels';

interface StageStepperProps {
  stages: StageItem[];
}

/** 执行阶段步骤条：桌面横向、移动端纵向，按阶段状态着色。 */
export function StageStepper({ stages }: StageStepperProps) {
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'));

  return (
    <Stepper
      activeStep={0}
      orientation={isDesktop ? 'horizontal' : 'vertical'}
      alternativeLabel={isDesktop}
      sx={{ py: 1 }}
    >
      {stages.map((stage) => (
        <Step
          key={stage.stage_name}
          active={stage.stage_status === 'running'}
          completed={stage.stage_status === 'success'}
        >
          <StepLabel
            error={stage.stage_status === 'failed'}
            optional={
              <Box
                sx={{
                  mt: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: isDesktop ? 'center' : 'flex-start',
                  gap: 0.5,
                }}
              >
                <StatusTag variant="stage" value={stage.stage_status} />
                <Typography variant="caption" color="text.secondary">
                  {formatDateTime(stage.started_at)} ~ {formatDateTime(stage.finished_at)}
                </Typography>
              </Box>
            }
          >
            {STAGE_NAME_LABELS[stage.stage_name]}
          </StepLabel>
        </Step>
      ))}
    </Stepper>
  );
}
