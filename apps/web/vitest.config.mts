import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    tsconfigPaths: true,
  },
  test: {
    environment: "jsdom",
    fileParallelism: false,
    maxWorkers: 1,
    setupFiles: ["./src/test/setup.ts"],
  },
});
