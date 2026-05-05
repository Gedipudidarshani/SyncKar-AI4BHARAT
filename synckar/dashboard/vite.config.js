import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // base must match the FastAPI mount path so asset URLs resolve correctly
  base: '/dashboard/',
  build: {
    rollupOptions: {
      // Single entry point — React Router handles all client-side routing
      input: 'index.html',
    },
  },
})
