import { expect, test } from '@playwright/test'
import { USERS, login, row } from './helpers'

/**
 * Known bugs (see docs/tester-guide.html → Known issues). Each is marked test.fail():
 * the suite stays green while the bug exists, and Playwright reports "expected to fail,
 * but passed" once it's fixed — then delete the test.fail() line.
 */

test('KI-1: clicking a customer row opens their details page', async ({ page }) => {
  test.fail(true, 'navigate(`/customers/${id}`) is missing the /app prefix → lands on Dashboard')
  await login(page, USERS.owner, '/app')
  await page.getByRole('link', { name: 'Customers' }).click()
  await row(page, 'Rahul Kumar').click()
  await expect(page).toHaveURL(/\/app\/customers\/[0-9a-f-]{36}$/, { timeout: 3000 })
})

test('KI-1: dashboard KPI card opens its page', async ({ page }) => {
  test.fail(true, "DashboardPage navigates to '/customers' etc. without the /app prefix")
  await login(page, USERS.owner, '/app')
  await page.getByText('Active Customers').first().click()
  await expect(page).toHaveURL(/\/app\/customers$/, { timeout: 3000 })
})

test('signup shows why a duplicate username was rejected', async ({ page }) => {
  test.fail(true, 'platformApi errMsg() shows only error.message ("Request failed.") and ignores error.fields → user never sees "Username already taken."')
  await page.goto('/signup')
  await page.getByPlaceholder("e.g. Rahul's Mess").fill('Duplicate Owner Mess')
  await page.getByPlaceholder('rahul', { exact: true }).fill('owner') // seeded username
  await page.getByPlaceholder('Min 8 characters').fill('whatever123')
  await page.getByRole('button', { name: 'Start Free Trial' }).click()
  await expect(page.getByText('Username already taken.')).toBeVisible({ timeout: 3000 })
})

test('staff form shows why a duplicate username was rejected', async ({ page }) => {
  test.fail(true, 'StaffForm shows only error.message ("Request failed.") and ignores error.fields')
  await login(page, USERS.owner, '/app')
  await page.getByRole('link', { name: 'Staff' }).click()
  await page.getByRole('button', { name: 'Add Staff' }).click()
  await page.getByLabel('Username').fill('delivery1')
  await page.getByLabel('Full Name').fill('Dup')
  await page.getByLabel('Password').fill('whatever123')
  await page.getByRole('button', { name: 'Create' }).click()
  await expect(page.getByText('Username already taken.')).toBeVisible({ timeout: 3000 })
})

test('KI-3: delivery staff can skip a pending delivery', async ({ page }) => {
  test.fail(true, 'Skip button is shown to DELIVERY_STAFF but the API only allows OWNER/MANAGER/CUSTOMER')
  await login(page, USERS.delivery, '/staff')
  const pending = page.getByRole('row').filter({ hasText: 'PENDING' }).first()
  const name = (await pending.locator('td').first().innerText()).trim()
  await pending.getByRole('button', { name: 'Skip' }).click()
  await expect(row(page, name).first()).toContainText('SKIPPED', { timeout: 3000 })
})
