import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Button from '@mui/material/Button';

interface ErrorAlertProps {
  message: string;
  title?: string;
  onRetry?: () => void;
}

/** 通用错误提示：可选重试按钮。 */
export function ErrorAlert({ message, title = '出错了', onRetry }: ErrorAlertProps) {
  return (
    <Alert
      severity="error"
      sx={{ mb: 2 }}
      action={
        onRetry !== undefined ? (
          <Button color="inherit" size="small" onClick={onRetry}>
            重试
          </Button>
        ) : undefined
      }
    >
      <AlertTitle>{title}</AlertTitle>
      {message}
    </Alert>
  );
}
