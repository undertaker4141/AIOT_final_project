import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:9547', changeOrigin: true },
      '/start': { target: 'http://localhost:9547', changeOrigin: true },
      '/end': { target: 'http://localhost:9547', changeOrigin: true },
      '/stream.mjpg': { target: 'http://localhost:9547', changeOrigin: true },
      '/ws': { target: 'ws://localhost:9548', ws: true, changeOrigin: true },
    },
  },
})
