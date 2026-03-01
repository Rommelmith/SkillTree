import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // Output into Django's static folder so whitenoise can serve it
    outDir: "../static/frontend",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // Fixed filenames so Django template can reference them without hashing
        entryFileNames: "js/main.js",
        chunkFileNames: "js/[name].js",
        assetFileNames: (assetInfo) => {
          if (assetInfo.name?.endsWith(".css")) return "css/main.css";
          return "assets/[name][extname]";
        },
      },
    },
  },
  server: {
    port: 5173,
    // Proxy API calls to Django dev server
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
