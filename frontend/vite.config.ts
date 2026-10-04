import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// In development the Vite server proxies /api to the FastAPI backend so the
// browser only ever talks to one origin (same as production behind nginx).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: process.env.VITE_API_PROXY ?? "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  test: {
    environment: "node",
  },
});
