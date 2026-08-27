import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import type { ResourceUsageItem } from '@/types/resource';

type ResourceMetric = 'cpu' | 'memory' | 'token';

interface ResourceChartProps {
  items: ResourceUsageItem[];
  metric: ResourceMetric;
}

const METRIC_META: Record<ResourceMetric, { label: string; unit: string }> = {
  cpu: { label: 'CPU 使用率', unit: '%' },
  memory: { label: '内存使用', unit: 'MB' },
  token: { label: 'Token 消耗', unit: '' },
};

const CHART_WIDTH = 600;
const CHART_HEIGHT = 140;
const PADDING = 10;

/** 自绘 SVG 折线图（无第三方图表库），展示资源消耗趋势。 */
export function ResourceChart({ items, metric }: ResourceChartProps) {
  const { label, unit } = METRIC_META[metric];
  const values = items
    .map((item) =>
      metric === 'cpu'
        ? item.cpu_usage
        : metric === 'memory'
          ? item.memory_usage
          : item.token_count,
    )
    .filter((value): value is number => value !== null && Number.isFinite(value));

  if (values.length === 0) {
    return (
      <Box>
        <Typography variant="subtitle2" gutterBottom>
          {label}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          暂无数据
        </Typography>
      </Box>
    );
  }

  const maxValue = Math.max(...values, 1) * 1.1;
  const innerWidth = CHART_WIDTH - PADDING * 2;
  const innerHeight = CHART_HEIGHT - PADDING * 2;
  const step = values.length > 1 ? innerWidth / (values.length - 1) : 0;
  const points = values.map((value, index) => ({
    x: PADDING + index * step,
    y: CHART_HEIGHT - PADDING - (value / maxValue) * innerHeight,
  }));
  const linePoints = points.map((point) => `${point.x},${point.y}`).join(' ');
  const lastPoint = points[points.length - 1];
  const areaPoints = `${PADDING},${CHART_HEIGHT - PADDING} ${linePoints} ${lastPoint.x},${CHART_HEIGHT - PADDING}`;
  const latestValue = values[values.length - 1];

  return (
    <Box>
      <Typography variant="subtitle2" gutterBottom>
        {label}（最新 {latestValue}
        {unit}）
      </Typography>
      <svg
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        role="img"
        aria-label={`${label}趋势图`}
        style={{ width: '100%', height: 'auto', display: 'block' }}
      >
        <line
          x1={PADDING}
          y1={CHART_HEIGHT - PADDING}
          x2={CHART_WIDTH - PADDING}
          y2={CHART_HEIGHT - PADDING}
          stroke="#e0e0e0"
          strokeWidth={1}
        />
        <polygon points={areaPoints} fill="#2563eb" opacity={0.12} />
        <polyline
          points={linePoints}
          fill="none"
          stroke="#2563eb"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        <text x={PADDING} y={PADDING + 8} fontSize={11} fill="#9e9e9e" textAnchor="start">
          峰值 {Math.max(...values).toFixed(0)}
          {unit}
        </text>
      </svg>
    </Box>
  );
}
