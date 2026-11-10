import { defineConfig, devices } from '@playwright/test'

/**
 * E2E tests run against an isolated stack, so they never touch your dev data:
 *   backend  → 127.0.0.1:8765, throwaway SQLite seeded fresh each run (e2e/start-backend.sh)
 *   frontend → localhost:5190, Vite dev server proxying /api to that backend
 *
 *   npm run e2e            headless
 *   npm run e2e:ui         Playwright UI mode
 *   npm run e2e:report     open the last HTML report
 */
// Dates in specs (isoDate) and in the browser must match the backend's "today" (Asia/Kolkata),
// otherwise runs between 00:00 and 05:30 IST on a UTC machine see yesterday.
process.env.TZ = 'Asia/Kolkata'

const API_PORT = process.env.E2E_API_PORT ?? '8765'
const WEB_PORT = process.env.E2E_WEB_PORT ?? '5190'

export default defineConfig({
  testDir: './e2e',
  // Specs share one seeded database and build on each other's data → run in order.
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 30_000,
  expect: { timeout: 7_000 },
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    timezoneId: 'Asia/Kolkata',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'bash e2e/start-backend.sh',
      url: `http://127.0.0.1:${API_PORT}/api/v1/pricing/`,
      env: { E2E_API_PORT: API_PORT },
      reuseExistingServer: false,
      timeout: 120_000,
      stdout: 'pipe',
    },
    {
      command: `npx vite --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      env: { VITE_PROXY_TARGET: `http://127.0.0.1:${API_PORT}` },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
})
