import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icons/icon-192.png'],
      manifest: {
        name: 'AI 读书会 · 陪读阅读器',
        short_name: 'AI读书',
        description: 'AI 陪你看小说，还能帮你改小说',
        theme_color: '#78716C',
        background_color: '#f6efe3',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,woff2,ico}'],
        runtimeCaching: [
          {
            urlPattern: /\/api\/(books|personas|density-profiles|health)/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'reader-api',
              expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 14 },
            },
          },
          {
            urlPattern: /\/api\/qrcode/,
            handler: 'StaleWhileRevalidate',
            options: { cacheName: 'reader-qr', expiration: { maxEntries: 50 } },
          },
        ],
      },
    }),
  ],
  server: {
    port: 5174,
    proxy: {
      '/api': 'http://127.0.0.1:8001',
      '/ws': { target: 'ws://127.0.0.1:8001', ws: true },
    },
  },
  build: { chunkSizeWarningLimit: 1200 },
})
