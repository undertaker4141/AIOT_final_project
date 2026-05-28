import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const host     = env.VITE_NODE_A_HOST      || 'localhost'
  const httpPort = env.VITE_NODE_A_HTTP_PORT || '9547'
  const wsPort   = env.VITE_NODE_A_WS_PORT   || '9548'
  const httpBase = `http://${host}:${httpPort}`
  const wsBase   = `ws://${host}:${wsPort}`

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        '/api':        { target: httpBase, changeOrigin: true },
        '/start':      { target: httpBase, changeOrigin: true },
        '/end':        { target: httpBase, changeOrigin: true },
        '/stream.mjpg':{ target: httpBase, changeOrigin: true },
        '/ws':         { target: wsBase,   ws: true, changeOrigin: true },
      },
    },
  }
})
