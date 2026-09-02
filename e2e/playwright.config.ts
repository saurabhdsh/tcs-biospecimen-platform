import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  timeout: 180000,
  expect: { timeout: 15000 },
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:5173",
    trace: "retain-on-failure",
  },
  reporter: [["list"]],
});
