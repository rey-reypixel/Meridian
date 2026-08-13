import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Native FS events from a Windows host bind-mount don't reliably
    // reach the Linux container - poll instead so hot-reload actually works.
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
})
