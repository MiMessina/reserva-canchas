import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
// El alias '@/' apunta a './src'. Vite resuelve la ruta relativa al root del proyecto.
// No usamos 'path' ni 'node:url' para evitar dependencia de @types/node antes de npm install.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // necesario para Docker (escucha en 0.0.0.0)
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})
