import { createTheme } from '@mui/material/styles';

/**
 * MUI 主题：品牌色 + 状态语义色，与状态标签组件共享配色约定。
 */
export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2563eb',
      light: '#60a5fa',
      dark: '#1d4ed8',
    },
    secondary: {
      main: '#64748b',
    },
    background: {
      default: '#f5f7fb',
      paper: '#ffffff',
    },
    success: {
      main: '#16a34a',
    },
    warning: {
      main: '#f59e0b',
    },
    error: {
      main: '#dc2626',
    },
    info: {
      main: '#0891b2',
    },
  },
  shape: {
    borderRadius: 8,
  },
  typography: {
    fontFamily: [
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      '"PingFang SC"',
      '"Microsoft YaHei"',
      'sans-serif',
    ].join(','),
  },
  components: {
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
    },
    MuiCard: {
      defaultProps: {
        variant: 'outlined',
      },
    },
  },
});
