import { defineConfig } from "vite";

export default defineConfig({
  base: "/proposalproof-genlayer-app/",
  build: {
    outDir: "pages-dist",
    emptyOutDir: true,
    rollupOptions: {
      input: "site-static/index.html",
    },
  },
});
