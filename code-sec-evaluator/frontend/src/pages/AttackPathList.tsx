import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import { useNavigate, useParams } from 'react-router-dom';

import { listAttackPaths } from '@/api/results';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/common/PageHeader';
import { useAsyncData } from '@/hooks/useAsyncData';
import { formatDateTime } from '@/utils/format';

/** 攻击路径列表页：路径编号、摘要、关联漏洞数与最终影响。 */
export function AttackPathList() {
  const params = useParams();
  const projectId = Number(params.projectId);
  const navigate = useNavigate();
  const { data, status, error, reload } = useAsyncData(() => listAttackPaths(projectId), projectId);

  const viewDetail = (pathId: number) => {
    navigate(`/projects/${projectId}/attack-paths/${pathId}`);
  };

  return (
    <Box>
      <PageHeader title="攻击路径" description="关联漏洞与利用顺序" />

      {status === 'loading' && <LoadingState label="正在加载攻击路径..." />}
      {status === 'error' && (
        <ErrorAlert message={error ?? '攻击路径加载失败'} onRetry={() => void reload()} />
      )}
      {status === 'success' &&
        (data === null || data.list.length === 0 ? (
          <EmptyState title="暂无攻击路径" description="评估完成后将在此整理攻击路径。" />
        ) : (
          <Paper>
            <TableContainer>
              <Table size="medium">
                <TableHead>
                  <TableRow>
                    <TableCell>编号</TableCell>
                    <TableCell>标题</TableCell>
                    <TableCell>摘要</TableCell>
                    <TableCell>关联漏洞</TableCell>
                    <TableCell>最终影响</TableCell>
                    <TableCell>创建时间</TableCell>
                    <TableCell align="right">操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.list.map((path) => (
                    <TableRow key={path.id} hover>
                      <TableCell>{path.path_code}</TableCell>
                      <TableCell>{path.path_title}</TableCell>
                      <TableCell sx={{ maxWidth: 280 }}>
                        <Typography variant="body2" noWrap>
                          {path.path_summary ?? '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>{path.vuln_count}</TableCell>
                      <TableCell sx={{ maxWidth: 240 }}>
                        <Typography variant="body2" noWrap>
                          {path.final_impact_text ?? '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>{formatDateTime(path.created_at)}</TableCell>
                      <TableCell align="right">
                        <Tooltip title="查看详情">
                          <span>
                            <IconButton size="small" onClick={() => viewDetail(path.id)}>
                              <VisibilityOutlinedIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        ))}

      <Stack spacing={1.5} sx={{ display: { xs: 'flex', md: 'none' }, mt: 2 }}>
        {data?.list.map((path) => (
          <Paper key={path.id} sx={{ p: 2, cursor: 'pointer' }} onClick={() => viewDetail(path.id)}>
            <Typography variant="subtitle2" fontWeight={600}>
              {path.path_code} · {path.path_title}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {path.path_summary ?? '-'}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              关联漏洞 {path.vuln_count} 个 · {formatDateTime(path.created_at)}
            </Typography>
          </Paper>
        ))}
      </Stack>
    </Box>
  );
}
