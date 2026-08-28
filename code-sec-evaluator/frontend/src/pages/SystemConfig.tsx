import RestartAltIcon from '@mui/icons-material/RestartAlt';
import SaveOutlinedIcon from '@mui/icons-material/SaveOutlined';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormHelperText from '@mui/material/FormHelperText';
import Grid from '@mui/material/Grid';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select, { type SelectChangeEvent } from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import Switch from '@mui/material/Switch';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useEffect, useMemo, useState, type ReactNode } from 'react';

import { ErrorAlert } from '@/components/common/ErrorAlert';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/common/PageHeader';
import { useConfigStore } from '@/store/configStore';
import type { ConfigUpdates } from '@/types/config';

interface ConfigFormState {
  defaultImage: string;
  mountReadonly: boolean;
  networkMode: string;
  defaultTimeoutSeconds: string;
  maxConcurrency: string;
  retentionDays: string;
  llmEnabled: boolean;
  llmBaseUrl: string;
  llmApiKey: string;
  clearLlmApiKey: boolean;
  llmModel: string;
}

interface ConfigFieldErrors {
  defaultImage?: string;
  defaultTimeoutSeconds?: string;
  maxConcurrency?: string;
  retentionDays?: string;
  llmBaseUrl?: string;
}

const NETWORK_MODES = ['none', 'internal', 'bridge'] as const;

function validateForm(form: ConfigFormState): ConfigFieldErrors {
  const errors: ConfigFieldErrors = {};
  if (form.defaultImage.trim() === '') {
    errors.defaultImage = '镜像名称不能为空';
  }
  if (!/^\d+$/.test(form.defaultTimeoutSeconds) || Number(form.defaultTimeoutSeconds) < 1) {
    errors.defaultTimeoutSeconds = '请输入正整数（秒）';
  }
  if (!/^\d+$/.test(form.maxConcurrency) || Number(form.maxConcurrency) < 1) {
    errors.maxConcurrency = '请输入正整数';
  }
  if (!/^\d+$/.test(form.retentionDays) || Number(form.retentionDays) < 1) {
    errors.retentionDays = '请输入正整数（天）';
  }
  const baseUrl = form.llmBaseUrl.trim();
  if (baseUrl !== '' && !/^https?:\/\/.+/.test(baseUrl)) {
    errors.llmBaseUrl = '请输入 http:// 或 https:// 开头的地址';
  }
  return errors;
}

interface SectionCardProps {
  title: string;
  description?: string;
  children: ReactNode;
}

function SectionCard({ title, description, children }: SectionCardProps) {
  return (
    <Card>
      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        {description !== undefined && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {description}
          </Typography>
        )}
        {children}
      </CardContent>
    </Card>
  );
}

/** 系统配置页：隔离环境 / 任务 / 保留策略的读取与更新（仅管理员可访问）。 */
export function SystemConfig() {
  const config = useConfigStore((state) => state.config);
  const status = useConfigStore((state) => state.status);
  const error = useConfigStore((state) => state.error);
  const saving = useConfigStore((state) => state.saving);
  const saveError = useConfigStore((state) => state.saveError);
  const fetchConfig = useConfigStore((state) => state.fetchConfig);
  const updateConfig = useConfigStore((state) => state.updateConfig);

  const [form, setForm] = useState<ConfigFormState>({
    defaultImage: '',
    mountReadonly: true,
    networkMode: 'none',
    defaultTimeoutSeconds: '',
    maxConcurrency: '',
    retentionDays: '',
    llmEnabled: false,
    llmBaseUrl: '',
    llmApiKey: '',
    clearLlmApiKey: false,
    llmModel: '',
  });
  const [fieldErrors, setFieldErrors] = useState<ConfigFieldErrors>({});
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    void fetchConfig();
  }, [fetchConfig]);

  useEffect(() => {
    if (config === null) {
      return;
    }
    setForm({
      defaultImage: config.isolation.default_image,
      mountReadonly: config.isolation.mount_readonly,
      networkMode: config.isolation.network_mode,
      defaultTimeoutSeconds: `${config.task.default_timeout_seconds}`,
      maxConcurrency: `${config.task.max_concurrency}`,
      retentionDays: `${config.retention.days}`,
      llmEnabled: config.llm.enabled,
      llmBaseUrl: config.llm.base_url,
      llmApiKey: '',
      clearLlmApiKey: false,
      llmModel: config.llm.model,
    });
    setFieldErrors({});
  }, [config]);

  const changedUpdates = useMemo<ConfigUpdates>(() => {
    if (config === null) {
      return {};
    }
    const updates: ConfigUpdates = {};
    const image = form.defaultImage.trim();
    if (image !== config.isolation.default_image) {
      updates['isolation.default_image'] = image;
    }
    if (form.mountReadonly !== config.isolation.mount_readonly) {
      updates['isolation.mount_readonly'] = form.mountReadonly;
    }
    if (form.networkMode !== config.isolation.network_mode) {
      updates['isolation.network_mode'] = form.networkMode;
    }
    const timeout = Number(form.defaultTimeoutSeconds);
    if (timeout !== config.task.default_timeout_seconds) {
      updates['task.default_timeout_seconds'] = timeout;
    }
    const concurrency = Number(form.maxConcurrency);
    if (concurrency !== config.task.max_concurrency) {
      updates['task.max_concurrency'] = concurrency;
    }
    const days = Number(form.retentionDays);
    if (days !== config.retention.days) {
      updates['retention.days'] = days;
    }
    if (form.llmEnabled !== config.llm.enabled) {
      updates['llm.enabled'] = form.llmEnabled;
    }
    const llmBaseUrl = form.llmBaseUrl.trim();
    if (llmBaseUrl !== config.llm.base_url) {
      updates['llm.base_url'] = llmBaseUrl;
    }
    const llmModel = form.llmModel.trim();
    if (llmModel !== config.llm.model) {
      updates['llm.model'] = llmModel;
    }
    const llmApiKey = form.llmApiKey.trim();
    if (llmApiKey !== '') {
      updates['llm.api_key'] = llmApiKey;
    } else if (form.clearLlmApiKey && config.llm.api_key_configured) {
      updates['llm.api_key'] = '';
    }
    return updates;
  }, [config, form]);

  const hasChanges = Object.keys(changedUpdates).length > 0;

  const updateField = <K extends keyof ConfigFormState>(key: K, value: ConfigFormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setFieldErrors({});
    setSaveSuccess(false);
  };

  const handleNetworkModeChange = (event: SelectChangeEvent<string>) => {
    updateField('networkMode', event.target.value);
  };

  const handleSave = async () => {
    const errors = validateForm(form);
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }
    if (!hasChanges) {
      return;
    }
    const ok = await updateConfig(changedUpdates);
    if (ok) {
      setSaveSuccess(true);
    }
  };

  const handleReset = () => {
    if (config === null) {
      return;
    }
    setForm({
      defaultImage: config.isolation.default_image,
      mountReadonly: config.isolation.mount_readonly,
      networkMode: config.isolation.network_mode,
      defaultTimeoutSeconds: `${config.task.default_timeout_seconds}`,
      maxConcurrency: `${config.task.max_concurrency}`,
      retentionDays: `${config.retention.days}`,
      llmEnabled: config.llm.enabled,
      llmBaseUrl: config.llm.base_url,
      llmApiKey: '',
      clearLlmApiKey: false,
      llmModel: config.llm.model,
    });
    setFieldErrors({});
    setSaveSuccess(false);
  };

  return (
    <Box>
      <PageHeader title="系统配置" description="隔离环境 / 任务 / 保留策略（仅管理员）" />

      {status === 'loading' && <LoadingState label="正在加载系统配置..." />}
      {status === 'error' && (
        <ErrorAlert message={error ?? '系统配置加载失败'} onRetry={() => void fetchConfig()} />
      )}
      {status === 'success' && config !== null && (
        <>
          {saveError !== null && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {saveError}
            </Alert>
          )}
          {saveSuccess && (
            <Alert severity="success" sx={{ mb: 2 }}>
              配置已保存，立即生效。
            </Alert>
          )}

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <SectionCard title="隔离环境" description="评估容器镜像与网络隔离策略">
                <Stack spacing={2.5}>
                  <TextField
                    label="默认镜像"
                    value={form.defaultImage}
                    onChange={(event) => updateField('defaultImage', event.target.value)}
                    error={fieldErrors.defaultImage !== undefined}
                    helperText={fieldErrors.defaultImage ?? '如 sec-evaluator:latest'}
                    fullWidth
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={form.mountReadonly}
                        onChange={(_event, checked) => updateField('mountReadonly', checked)}
                      />
                    }
                    label="源码只读挂载"
                  />
                  <FormControl fullWidth>
                    <InputLabel id="network-mode-label">网络模式</InputLabel>
                    <Select
                      labelId="network-mode-label"
                      label="网络模式"
                      value={form.networkMode}
                      onChange={handleNetworkModeChange}
                    >
                      {NETWORK_MODES.map((mode) => (
                        <MenuItem key={mode} value={mode}>
                          {mode}
                        </MenuItem>
                      ))}
                    </Select>
                    <FormHelperText>建议 none（无网络），隔离评估更安全</FormHelperText>
                  </FormControl>
                </Stack>
              </SectionCard>
            </Grid>

            <Grid item xs={12} md={6}>
              <SectionCard title="任务调度" description="阶段超时与并行评估数">
                <Stack spacing={2.5}>
                  <TextField
                    label="阶段默认超时（秒）"
                    value={form.defaultTimeoutSeconds}
                    onChange={(event) => updateField('defaultTimeoutSeconds', event.target.value)}
                    error={fieldErrors.defaultTimeoutSeconds !== undefined}
                    helperText={fieldErrors.defaultTimeoutSeconds ?? '超时后阶段标记 failed'}
                    inputMode="numeric"
                    fullWidth
                  />
                  <TextField
                    label="最大并发评估项目数"
                    value={form.maxConcurrency}
                    onChange={(event) => updateField('maxConcurrency', event.target.value)}
                    error={fieldErrors.maxConcurrency !== undefined}
                    helperText={fieldErrors.maxConcurrency ?? '同时运行的项目数上限'}
                    inputMode="numeric"
                    fullWidth
                  />
                </Stack>
              </SectionCard>
            </Grid>

            <Grid item xs={12} md={6}>
              <SectionCard title="保留策略" description="已完成项目的文件保留天数">
                <TextField
                  label="保留天数"
                  value={form.retentionDays}
                  onChange={(event) => updateField('retentionDays', event.target.value)}
                  error={fieldErrors.retentionDays !== undefined}
                  helperText={fieldErrors.retentionDays ?? '到期后定期清理日志/报告/工作区'}
                  inputMode="numeric"
                  fullWidth
                />
              </SectionCard>
            </Grid>

            <Grid item xs={12} md={6}>
              <SectionCard title="LLM 分析" description="开关与模型参数，仅影响之后启动的项目">
                <Stack spacing={2.5}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={form.llmEnabled}
                        onChange={(_event, checked) => updateField('llmEnabled', checked)}
                      />
                    }
                    label="启用 LLM 语义分析"
                  />
                  <TextField
                    label="Base URL"
                    value={form.llmBaseUrl}
                    onChange={(event) => updateField('llmBaseUrl', event.target.value)}
                    error={fieldErrors.llmBaseUrl !== undefined}
                    helperText={fieldErrors.llmBaseUrl ?? '留空使用 .env 中的 LLM_BASE_URL'}
                    placeholder="https://api.example.com/v1"
                    fullWidth
                  />
                  <TextField
                    label="Model"
                    value={form.llmModel}
                    onChange={(event) => updateField('llmModel', event.target.value)}
                    helperText="留空使用 .env 中的 LLM_MODEL"
                    placeholder="gpt-4.1-mini"
                    fullWidth
                  />
                  <TextField
                    label="API Key"
                    value={form.llmApiKey}
                    onChange={(event) => updateField('llmApiKey', event.target.value)}
                    helperText={
                      config.llm.api_key_configured
                        ? '已保存用户提供的 API Key；留空保持不变'
                        : '留空使用 .env 中的 LLM_API_KEY'
                    }
                    type="password"
                    autoComplete="new-password"
                    fullWidth
                  />
                  {config.llm.api_key_configured && (
                    <FormControlLabel
                      control={
                        <Switch
                          checked={form.clearLlmApiKey}
                          onChange={(_event, checked) => updateField('clearLlmApiKey', checked)}
                          disabled={form.llmApiKey.trim() !== ''}
                        />
                      }
                      label="清除已保存的 API Key"
                    />
                  )}
                </Stack>
              </SectionCard>
            </Grid>
          </Grid>

          <Stack direction="row" spacing={2} sx={{ mt: 3, justifyContent: 'flex-end' }}>
            <Button
              variant="outlined"
              startIcon={<RestartAltIcon />}
              onClick={handleReset}
              disabled={saving}
            >
              重置
            </Button>
            <Button
              variant="contained"
              startIcon={<SaveOutlinedIcon />}
              onClick={() => void handleSave()}
              disabled={saving || !hasChanges}
            >
              {saving ? '保存中...' : '保存配置'}
            </Button>
          </Stack>
        </>
      )}
    </Box>
  );
}
