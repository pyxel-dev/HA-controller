import {defineConfig} from "vitest/config";

export default defineConfig({
  build: {
    lib: {
      entry: "src/ha-controller-panel.ts",
      formats: ["es"],
      fileName: () => "ha-controller-panel.js",
    },
    outDir: "dist",
    emptyOutDir: true,
    target: "es2022",
  },
  server: {fs: {allow: ["../../.."]}},
  test: {environment: "happy-dom"},
});
