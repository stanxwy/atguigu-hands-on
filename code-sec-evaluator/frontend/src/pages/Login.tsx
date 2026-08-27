import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Link from '@mui/material/Link';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { useAuthStore } from '@/store/authStore';

const PASSWORD_CATEGORY_PATTERNS = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^A-Za-z0-9]/];

interface LocationState {
  from?: {
    pathname?: string;
  };
}

interface LoginFieldErrors {
  username?: string;
  password?: string;
  confirmPassword?: string;
}

/** 密码强度校验（与后端 InitRequest 校验一致）。 */
function validatePasswordStrength(value: string): string | null {
  if (value.length < 8 || value.length > 64) {
    return '密码长度须为 8~64 位';
  }
  const matchedCategories = PASSWORD_CATEGORY_PATTERNS.filter((pattern) =>
    pattern.test(value),
  ).length;
  if (matchedCategories < 3) {
    return '密码须包含大写/小写/数字/特殊字符中的至少三类';
  }
  if (new TextEncoder().encode(value).length > 72) {
    return '密码过长（bcrypt 上限 72 字节）';
  }
  return null;
}

/** 登录页：登录模式 + 首次初始化管理员模式（切换式）。 */
export function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const status = useAuthStore((state) => state.status);
  const error = useAuthStore((state) => state.error);
  const login = useAuthStore((state) => state.login);
  const initSystem = useAuthStore((state) => state.initSystem);
  const resetError = useAuthStore((state) => state.resetError);

  const [mode, setMode] = useState<'login' | 'init'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState<LoginFieldErrors>({});
  const [initSuccess, setInitSuccess] = useState(false);

  const isLoading = status === 'loading';

  if (user !== null) {
    return <Navigate to="/projects" replace />;
  }

  const switchMode = (nextMode: 'login' | 'init') => {
    setMode(nextMode);
    setFieldErrors({});
    setInitSuccess(false);
    resetError();
  };

  const handleLoginSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const errors: LoginFieldErrors = {};
    if (username.trim() === '') {
      errors.username = '请输入用户名';
    }
    if (password === '') {
      errors.password = '请输入密码';
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }
    const ok = await login(username.trim(), password);
    if (ok) {
      const from = (location.state as LocationState | null)?.from?.pathname;
      navigate(from ?? '/projects', { replace: true });
    }
  };

  const handleInitSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const errors: LoginFieldErrors = {};
    if (username.trim() === '') {
      errors.username = '请输入用户名';
    }
    const passwordError = validatePasswordStrength(password);
    if (passwordError !== null) {
      errors.password = passwordError;
    }
    if (password !== confirmPassword) {
      errors.confirmPassword = '两次输入的密码不一致';
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }
    const ok = await initSystem(username.trim(), password);
    if (ok) {
      setInitSuccess(true);
      setMode('login');
      setPassword('');
      setConfirmPassword('');
      resetError();
    }
  };

  const handleModeChange = (nextMode: 'login' | 'init') => {
    switchMode(nextMode);
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2,
        bgcolor: 'background.default',
      }}
    >
      <Card sx={{ width: '100%', maxWidth: 420 }}>
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={3}>
            <Box sx={{ textAlign: 'center' }}>
              <Box sx={{ fontSize: 40, mb: 1 }}>🛡</Box>
              <Typography variant="h5" component="h1" gutterBottom>
                自动化安全评估系统
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {mode === 'login' ? '登录以继续' : '初始化管理员账户'}
              </Typography>
            </Box>

            {error !== null && <Alert severity="error">{error}</Alert>}
            {mode === 'login' && initSuccess && (
              <Alert severity="success">管理员账户创建成功，请使用新账户登录。</Alert>
            )}

            <Box
              component="form"
              onSubmit={mode === 'login' ? handleLoginSubmit : handleInitSubmit}
              noValidate
            >
              <Stack spacing={2.5}>
                <TextField
                  label="用户名"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  error={fieldErrors.username !== undefined}
                  helperText={fieldErrors.username}
                  autoComplete="username"
                  fullWidth
                />
                <TextField
                  label="密码"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  error={fieldErrors.password !== undefined}
                  helperText={fieldErrors.password}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  fullWidth
                />
                {mode === 'init' && (
                  <TextField
                    label="确认密码"
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    error={fieldErrors.confirmPassword !== undefined}
                    helperText={fieldErrors.confirmPassword}
                    autoComplete="new-password"
                    fullWidth
                  />
                )}
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  startIcon={<LockOutlinedIcon />}
                  disabled={isLoading}
                  fullWidth
                >
                  {isLoading ? '提交中...' : mode === 'login' ? '登录' : '创建管理员'}
                </Button>
              </Stack>
            </Box>

            <Typography variant="body2" align="center">
              {mode === 'login' ? (
                <>
                  首次使用？{' '}
                  <Link component="button" type="button" onClick={() => handleModeChange('init')}>
                    初始化管理员账户
                  </Link>
                </>
              ) : (
                <Link component="button" type="button" onClick={() => handleModeChange('login')}>
                  返回登录
                </Link>
              )}
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
