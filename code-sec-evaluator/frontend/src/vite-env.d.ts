/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** API 基础路径（默认 /api，经 Vite 代理转发到后端）。 */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
