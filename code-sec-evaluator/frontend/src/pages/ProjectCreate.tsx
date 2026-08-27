import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormLabel from '@mui/material/FormLabel';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { PageHeader } from '@/components/common/PageHeader';
import { useProjectStore } from '@/store/projectStore';
import { SOURCE_TYPES } from '@/types/enums';
import type { SourceType } from '@/types/enums';

interface CreateFieldErrors {
  projectName?: string;
  sourcePath?: string;
  taskContent?: string;
}

/** 创建项目页：表单校验与后端 schema 对齐。 */
export function ProjectCreate() {
  const navigate = useNavigate();
  const operationStatus = useProjectStore((state) => state.operationStatus);
  const operationError = useProjectStore((state) => state.operationError);
  const createProject = useProjectStore((state) => state.createProject);
  const resetOperationError = useProjectStore((state) => state.resetOperationError);

  const [projectName, setProjectName] = useState('');
  const [sourceType, setSourceType] = useState<SourceType>('local_path');
  const [sourcePath, setSourcePath] = useState('');
  const [taskContent, setTaskContent] = useState('');
  const [fieldErrors, setFieldErrors] = useState<CreateFieldErrors>({});

  useEffect(() => {
    resetOperationError();
  }, [resetOperationError]);

  const handleSourceTypeChange = (event: ChangeEvent<HTMLInputElement>) => {
    setSourceType(event.target.value as SourceType);
    setFieldErrors((prev) => ({ ...prev, sourcePath: undefined }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const errors: CreateFieldErrors = {};
    const name = projectName.trim();
    const path = sourcePath.trim();
    const content = taskContent.trim();

    if (name === '' || name.length > 128) {
      errors.projectName = '项目名称须为 1~128 个字符';
    }
    if (path === '') {
      errors.sourcePath = '请输入源码路径或仓库地址';
    } else if (sourceType === 'local_path') {
      const isAbsolute =
        /^[A-Za-z]:[\\/]/.test(path) || path.startsWith('/') || path.startsWith('\\\\');
      if (!isAbsolute) {
        errors.sourcePath = '本地路径须为绝对路径（如 C:\\projects\\demo 或 /data/src/demo）';
      }
    } else if (!/^https:\/\/[^\s]+\.git$/.test(path)) {
      errors.sourcePath = '仓库地址须为 https:// 开头的 .git 地址';
    }
    if (content.length > 4096) {
      errors.taskContent = '任务说明不能超过 4096 个字符';
    }

    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }

    const createdId = await createProject({
      project_name: name,
      source_type: sourceType,
      source_path: path,
      task_content: content === '' ? null : content,
    });
    if (createdId !== null) {
      navigate(`/projects/${createdId}`);
    }
  };

  return (
    <Box sx={{ maxWidth: 720, mx: 'auto' }}>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/projects')} sx={{ mb: 2 }}>
        返回项目列表
      </Button>
      <PageHeader title="创建评估项目" description="接入本地源码路径或公开 Git 仓库" />

      <Card>
        <CardContent sx={{ p: { xs: 2, sm: 4 } }}>
          {operationError !== null && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {operationError}
            </Alert>
          )}
          <Box component="form" onSubmit={handleSubmit} noValidate>
            <Stack spacing={3}>
              <TextField
                label="项目名称"
                value={projectName}
                onChange={(event) => setProjectName(event.target.value)}
                error={fieldErrors.projectName !== undefined}
                helperText={fieldErrors.projectName ?? '用于标识本次评估任务'}
                fullWidth
              />

              <Box>
                <FormLabel component="legend">源码来源</FormLabel>
                <RadioGroup row value={sourceType} onChange={handleSourceTypeChange}>
                  {SOURCE_TYPES.map((type) => (
                    <FormControlLabel
                      key={type}
                      value={type}
                      control={<Radio />}
                      label={type === 'local_path' ? '本地路径' : 'Git 仓库'}
                    />
                  ))}
                </RadioGroup>
              </Box>

              <TextField
                label={sourceType === 'local_path' ? '源码绝对路径' : 'Git 仓库地址'}
                value={sourcePath}
                onChange={(event) => setSourcePath(event.target.value)}
                error={fieldErrors.sourcePath !== undefined}
                helperText={
                  fieldErrors.sourcePath ??
                  (sourceType === 'local_path'
                    ? '示例：C:\\projects\\demo 或 /data/src/demo'
                    : '仅支持 https:// 开头的公开 .git 地址')
                }
                fullWidth
              />

              <TextField
                label="任务说明（可选）"
                value={taskContent}
                onChange={(event) => setTaskContent(event.target.value)}
                error={fieldErrors.taskContent !== undefined}
                helperText={fieldErrors.taskContent ?? '例如：重点评估注入类漏洞'}
                multiline
                minRows={4}
                fullWidth
              />

              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={2}
                sx={{ justifyContent: 'flex-end' }}
              >
                <Button variant="outlined" onClick={() => navigate('/projects')}>
                  取消
                </Button>
                <Button type="submit" variant="contained" disabled={operationStatus === 'loading'}>
                  {operationStatus === 'loading' ? '创建中...' : '创建项目'}
                </Button>
              </Stack>
            </Stack>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
