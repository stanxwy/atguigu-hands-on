/**
 * 时间格式化工具：后端返回 ISO 时间字符串，统一转为本地可读格式。
 */
export function formatDateTime(value: string | null): string {
  if (value === null || value === '') {
    return '-';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
}
