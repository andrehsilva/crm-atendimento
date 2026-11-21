import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Durante o desenvolvimento, chamadas a /api e /health vão para o backend (porta 8000).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/site': 'http://localhost:8000', // Etapa 11: site de apresentação de cada clínica
    },
  },
})
