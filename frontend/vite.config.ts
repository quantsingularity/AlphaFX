import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Forward /api/* and /ws/* to the Django backend during local dev.
      // The path is passed through unchanged -- the backend serves at /api/v1/...
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          // Core framework
          "vendor-react": ["react", "react-dom", "react-router-dom"],
          // Data fetching
          "vendor-query": ["react-query", "axios"],
          // Charts
          "vendor-charts": ["recharts"],
        },
      },
    },
  },
});
