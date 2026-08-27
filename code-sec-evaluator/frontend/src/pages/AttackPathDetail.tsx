import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import { useNavigate, useParams } from 'react-router-dom';

import { getAttackPath } from '@/api/results';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/common/PageHeader';
import { useAsyncData } from '@/hooks/useAsyncData';

/** 攻击路径详情页：路径概述 + 按顺序的利用步骤（可跳转关联漏洞）。 */
export function AttackPathDetail() {
  const params = useParams();
  const projectId = Number(params.projectId);
  const pathId = Number(params.pathId);
  const navigate = useNavigate();
  const {
    data: path,
    status,
    error,
    reload,
  } = useAsyncData(() => getAttackPath(projectId, pathId), `${projectId}:${pathId}`);

  if (status === 'loading') {
    return <LoadingState label="正在加载攻击路径..." />;
  }
  if (status === 'error' || path === null) {
    return (
      <Box>
        <ErrorAlert message={error ?? '攻击路径加载失败'} onRetry={() => void reload()} />
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(`/projects/${projectId}/attack-paths`)}
        >
          返回攻击路径列表
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate(`/projects/${projectId}/attack-paths`)}
        sx={{ mb: 2 }}
      >
        返回攻击路径列表
      </Button>
      <PageHeader title={`${path.path_code} · ${path.path_title}`} description="攻击路径详情" />

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          路径摘要
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {path.path_summary ?? '-'}
        </Typography>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          最终影响
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {path.final_impact_text ?? '-'}
        </Typography>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>
          利用步骤
        </Typography>
        {path.items.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            暂无步骤。
          </Typography>
        ) : (
          <List disablePadding>
            {path.items.map((item) => (
              <ListItem key={item.step_order} sx={{ px: 0, alignItems: 'flex-start' }}>
                <Avatar
                  sx={{
                    bgcolor: 'primary.main',
                    width: 28,
                    height: 28,
                    fontSize: 14,
                    mr: 2,
                    mt: 0.5,
                  }}
                >
                  {item.step_order}
                </Avatar>
                <Box sx={{ minWidth: 0 }}>
                  <Typography
                    variant="body2"
                    sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
                  >
                    {item.step_text ?? '-'}
                  </Typography>
                  {item.vuln_code !== null && (
                    <Link
                      component="button"
                      variant="body2"
                      underline="hover"
                      onClick={() =>
                        navigate(`/projects/${projectId}/vulnerabilities/${item.vuln_id}`)
                      }
                      sx={{ mt: 0.5, display: 'inline-block' }}
                    >
                      {item.vuln_code} - {item.vuln_title ?? '关联漏洞'}
                    </Link>
                  )}
                </Box>
              </ListItem>
            ))}
          </List>
        )}
      </Paper>
    </Box>
  );
}
