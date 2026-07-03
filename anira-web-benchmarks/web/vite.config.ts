import { defineConfig } from 'vite'

const CORS_HEADERS = {
  'Cross-Origin-Embedder-Policy': 'require-corp',
  'Cross-Origin-Opener-Policy': 'same-origin',
}

export default defineConfig({
  base: '/',
  assetsInclude: ['**/*.wasm'],
  build: {
    target: 'esnext',
    assetsInlineLimit: 0,
    rollupOptions: {
      input: './index.html',
      output: { format: 'es' },
    },
  },
  worker: { format: 'es' },
  server: { headers: CORS_HEADERS, fs: { strict: false } },
  preview: { headers: CORS_HEADERS },
})
