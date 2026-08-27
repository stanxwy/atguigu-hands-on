import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';

type DialogSeverity = 'info' | 'warning' | 'error';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  loading?: boolean;
  severity?: DialogSeverity;
  onConfirm: () => void;
  onClose: () => void;
}

const SEVERITY_BUTTON_COLOR: Record<DialogSeverity, 'primary' | 'warning' | 'error'> = {
  info: 'primary',
  warning: 'warning',
  error: 'error',
};

/** 通用确认对话框：用于启动/停止/删除等操作的二次确认。 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmText = '确认',
  cancelText = '取消',
  loading = false,
  severity = 'warning',
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onClose={loading ? undefined : onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      {description !== undefined && (
        <DialogContent>
          <DialogContentText>{description}</DialogContentText>
        </DialogContent>
      )}
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>
          {cancelText}
        </Button>
        <Button
          onClick={onConfirm}
          color={SEVERITY_BUTTON_COLOR[severity]}
          variant="contained"
          disabled={loading}
          autoFocus
        >
          {loading ? '处理中...' : confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
