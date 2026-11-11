import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, proxy API calls to the FastAPI backend. In production the backend serves the
// built static files from the same origin (ADR-10), so no proxy is needed.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});
