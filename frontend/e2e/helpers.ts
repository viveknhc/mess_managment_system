import { expect, type Locator, type Page } from '@playwright/test'

/** Seeded demo accounts (backend seed_data + e2e/start-backend.sh). */
export const USERS = {
  superadmin: { username: 'superadmin', password: 'superadmin123', home: '/platform' },
  owner: { username: 'owner', password: 'owner123', home: '/app' },
  manager: { username: 'manager', password: 'manager123', home: '/app' },
  delivery: { username: 'delivery1', password: 'delivery123', home: '/staff' },
  kitchen: { username: 'kitchen1', password: 'kitchen123', home: '/staff' },
  customer1: { username: 'customer1', password: 'customer123', home: '/portal' }, // Rahul — Weekly Breakfast (no pause)
  customer2: { username: 'customer2', password: 'customer123', home: '/portal' }, // Priya — Fortnightly Lunch
  customer3: { username: 'customer3', password: 'customer123', home: '/portal' }, // Amit — Monthly Lunch
  customer4: { username: 'customer4', password: 'customer123', home: '/portal' }, // Sneha — Monthly Dinner
  customer5: { username: 'customer5', password: 'customer123', home: '/portal' }, // Vikram Joshi — Monthly Full Meals
} as const

export type Creds = { username: string; password: string }

export async function login(page: Page, user: Creds, expectedPath?: string) {
  await page.goto('/login')
  await page.getByLabel('Username').fill(user.username)
  await page.getByLabel('Password').fill(user.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  if (expectedPath) await expect(page).toHaveURL(new RegExp(`${expectedPath}(/|$)`))
}

export async function logout(page: Page) {
  await page.getByRole('button', { name: 'Logout' }).click()
  await expect(page).toHaveURL(/\/login$/)
}

/** Input/select/textarea that directly follows a <label> with this exact text (for forms without htmlFor). */
export function field(scope: Page | Locator, label: string): Locator {
  return scope.locator(
    `label:text-is("${label}") + input, label:text-is("${label}") + select, label:text-is("${label}") + textarea`,
  )
}

/** Select the <option> whose text contains `text` (option labels carry dynamic suffixes like "(CUST-0021)"). */
export async function selectByText(select: Locator, text: string) {
  const option = select.locator('option', { hasText: text }).first()
  await expect(option).toBeAttached()
  await select.selectOption((await option.getAttribute('value'))!)
}

/** Local YYYY-MM-DD, `offset` days from today (backend and browser share this machine's clock). */
export function isoDate(offset = 0): string {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** Short unique suffix so specs can be re-run against the same database. */
export const uniq = () => Date.now().toString(36).slice(-5)

/** The modal overlay used by every form/dialog in the app. */
export const modal = (page: Page) => page.locator('div.fixed.inset-0').last()

/** Status filter tab (e.g. "Pending") — not the identically-named sortable column header, which has a title. */
export const tab = (page: Page, name: string) =>
  page.getByRole('button', { name, exact: true }).and(page.locator('button:not([title])'))

/** Table row containing `text`. */
export const row = (page: Page, text: string | RegExp) => page.getByRole('row').filter({ hasText: text })

/** Parse "₹1,234.50" → 1234.5 */
export const rupees = (s: string) => Number(s.replace(/[^0-9.]/g, ''))

/** API login (for test setup that would be slow or irrelevant through the UI). */
export async function apiToken(page: Page, user: Creds): Promise<string> {
  const res = await page.request.post('/api/v1/auth/login/', { data: user })
  expect(res.ok()).toBeTruthy()
  return (await res.json()).access
}
