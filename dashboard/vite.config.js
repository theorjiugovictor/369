import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3369,
    proxy: {
      '/api': 'http://localhost:8369',
      '/health': 'http://localhost:8369',
    },
  },
  build: {
    outDir: 'dist',
  },
})
