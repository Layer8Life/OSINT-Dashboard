import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base so the build works on any GitHub Pages sub-path.
export default defineConfig({
  base: "./",
  plugins: [react()],
  // three.js + globe.gl alone are ~2 MB; one chunk is fine for this app.
  build: { chunkSizeWarningLimit: 3000 },
});
