/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  if (mode === 'production' && env.VITE_USE_MOCKS === 'true') {
    throw new Error('VITE_USE_MOCKS must never be enabled for production builds.');
  }
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      // In normal dev mode, forward API calls to the real backend (same-origin → HttpOnly cookies work).
      proxy: {
        '/api': { target: env.VITE_API_PROXY || 'http://localhost:8000', changeOrigin: true },
        // Images uploaded through the admin's question editor.
        '/media': { target: env.VITE_API_PROXY || 'http://localhost:8000', changeOrigin: true },
      },
    },
    test: { environment: 'node', include: ['src/**/*.test.ts'] },
  };
});
