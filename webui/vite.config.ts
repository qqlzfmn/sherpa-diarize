import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 后端固定运行在 127.0.0.1:8000（examples/web/server.py），前端一律使用相对路径，
// 开发时由 vite 代理转发；构建产物由后端直接托管（同源，无需代理）。
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/models': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
    },
  },
})
