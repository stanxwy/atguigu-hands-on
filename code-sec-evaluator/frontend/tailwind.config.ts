import type { Config } from 'tailwindcss';

/**
 * Tailwind 配置：关闭 preflight，避免与 MUI 基线样式冲突；
 * 仅作为原子化布局辅助（间距 / flex / 文本截断等）。
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {},
  },
  corePlugins: {
    preflight: false,
  },
  plugins: [],
} satisfies Config;
