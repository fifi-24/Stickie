import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    // Vite blocks requests with an unrecognized Host header by default
    // (DNS-rebinding protection) — without this, the site 403s the
    // instant it's opened through a tunnel instead of localhost.
    allowedHosts: true,
  },
})