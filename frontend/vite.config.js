import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  test: {
    environment: 'happy-dom', // provides localStorage, window and document
  },
  server: {
    port: 5173,
    // In development, /api is forwarded to FastAPI so no CORS setup is needed.
    proxy: { '/api': 'http://localhost:8000' },
  },
})
