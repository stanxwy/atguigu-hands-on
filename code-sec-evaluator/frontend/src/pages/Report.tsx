import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import { useParams } from 'react-router-dom';

import { downloadReport, getReport } from '@/api/results';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/common/PageHeader';
import { ReportViewer } from '@/components/report/ReportViewer';
import { useAsyncData } from '@/hooks/useAsyncData';

/** 报告页：Markdown 安全预览 / HTML 沙箱预览 / 下载。 */
export function Report() {
  const params = useParams();
  const projectId = Number(params.projectId);
  const {
    data: report,
    status,
    error,
    reload,
  } = useAsyncData(() => getReport(projectId), projectId);
  const isMissing = error !== null && error.includes('报告不存在');

  return (
    <Box>
      <PageHeader title="评估报告" description="预览与下载最终报告" />

      {status === 'loading' && <LoadingState label="正在加载报告..." />}
      {status === 'error' && !isMissing && (
        <ErrorAlert message={error ?? '报告加载失败'} onRetry={() => void reload()} />
      )}
      {isMissing && (
        <EmptyState
          title="报告尚未生成"
          description="评估完成后将自动生成最终报告，可稍后刷新查看。"
          action={
            <Button variant="outlined" onClick={() => void reload()}>
              刷新
            </Button>
          }
        />
      )}
      {status === 'success' && report !== null && (
        <ReportViewer
          markdown={report.report_markdown}
          html={report.report_html}
          createdAt={report.created_at}
          onDownload={() => void downloadReport(projectId)}
        />
      )}
    </Box>
  );
}
