/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * 后端地址。留空则使用同源（本地 dev 的 Vite 代理 / 单服务部署）。
   * 可写完整 URL（https://api.example.com）或仅主机名（api.example.com，自动补 https）。
   */
  readonly VITE_API_BASE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
