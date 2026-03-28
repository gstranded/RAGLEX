import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const devPort = Number(process.env.FRONTEND_PORT || process.env.VITE_DEV_PORT || 13000)
const proxyTarget = process.env.VITE_PROXY_TARGET || process.env.BACKEND_URL || 'http://127.0.0.1:5000'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: devPort,
    open: false,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    outDir: 'dist' // 构建输出目录
  }
})
