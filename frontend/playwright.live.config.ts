import { defineConfig, devices } from "@playwright/test";

/**
 * LIVE-mode browser check against the deployed AWS backend. Not part of `npm run test:e2e` (that stays AWS-free).
 *   npm run build && npx next start -p 3000        # with frontend/.env.local from infrastructure/scripts/70-frontend-env.sh
 *   npx playwright test -c playwright.live.config.ts
 */
export default defineConfig({
  testDir: "./tests/e2e-live",
  timeout: 120_000,
  use: { baseURL: "http://localhost:3000", actionTimeout: 30_000, screenshot: "only-on-failure" },
  projects: [{ name: "live-desktop", use: { ...devices["Desktop Chrome"], channel: "chrome", viewport: { width: 1280, height: 800 } } }],
});
