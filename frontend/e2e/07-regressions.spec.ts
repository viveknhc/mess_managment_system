import { expect, test } from '@playwright/test'
import { USERS, login, row } from './helpers'

/**
 * Regression tests for bugs found by this suite (fixed Nov 2026):
 *   - links missing the /app prefix (customer rows, dashboard cards)
 *   - validation errors hidden behind a generic "Request failed."
 *   - Skip shown to delivery staff, who aren't allowed to skip
 *   - kitchen summary failing because it fetched the delivery list
 * (Kitchen routing and the wrong-password message are covered in 01-auth.)
 */

test('clicking a customer row opens their details page', async ({ page }) => {
  await login(page, USERS.owner, '/app')
  await page.getByRole('link', { name: 'Customers' }).click()
  await row(page, 'Rahul Kumar').click()
  await expect(page).toHaveURL(/\/app\/customers\/[0-9a-f-]{36}$/)
  await expect(page.getByRole('heading', { name: 'Rahul Kumar' })).toBeVisible()
  await page.getByRole('button', { name: /Customers/ }).first().click()
  await expect(page).toHaveURL(/\/app\/customers$/)
})

test('dashboard KPI cards and quick actions open their pages', async ({ page }) => {
  await login(page, USERS.owner, '/app')
  await page.getByText('Active Customers').first().click()
  await expect(page).toHaveURL(/\/app\/customers$/)
  await page.getByRole('link', { name: 'Dashboard' }).click()
  await page.getByRole('button', { name: 'Record Payment' }).click()
  await expect(page).toHaveURL(/\/app\/payments$/)
})

test('signup explains why a duplicate username was rejected', async ({ page }) => {
  await page.goto('/signup')
  await page.getByPlaceholder("e.g. Rahul's Mess").fill('Duplicate Owner Mess')
  await page.getByPlaceholder('rahul', { exact: true }).fill('owner') // seeded username
  await page.getByPlaceholder('Min 8 characters').fill('whatever123')
  await page.getByRole('button', { name: 'Start Free Trial' }).click()
  await expect(page.getByText('Username already taken.')).toBeVisible()
  await expect(page.getByText('Request failed.')).toHaveCount(0)
})

test('staff form explains why a duplicate username was rejected', async ({ page }) => {
  await login(page, USERS.owner, '/app')
  await page.getByRole('link', { name: 'Staff' }).click()
  await page.getByRole('button', { name: 'Add Staff' }).click()
  await page.getByLabel('Username').fill('delivery1')
  await page.getByLabel('Full Name').fill('Dup')
  await page.getByLabel('Password').fill('whatever123')
  await page.getByRole('button', { name: 'Create' }).click()
  await expect(page.getByText(/username already exists/i)).toBeVisible()
  await expect(page.getByText('Request failed.')).toHaveCount(0)
})

test('delivery staff record outcomes but cannot skip; owner can', async ({ page, browser }) => {
  await login(page, USERS.delivery, '/staff')
  const pending = page.getByRole('row').filter({ hasText: 'PENDING' }).first()
  await expect(pending.getByRole('button', { name: 'Delivered', exact: true })).toBeVisible()
  await expect(pending.getByRole('button', { name: 'Not Delivered' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Skip', exact: true })).toHaveCount(0)

  const owner = await (await browser.newContext()).newPage()
  await login(owner, USERS.owner, '/app')
  await owner.getByRole('link', { name: 'Deliveries' }).click()
  const ownerPending = owner.getByRole('row').filter({ hasText: 'PENDING' }).first()
  const name = (await ownerPending.locator('td').first().innerText()).trim()
  await ownerPending.getByRole('button', { name: 'Skip', exact: true }).click()
  await expect(row(owner, name).filter({ hasText: 'SKIPPED' }).first()).toBeVisible()
})

test('kitchen sees meal counts and the delivery-outcome summary', async ({ page }) => {
  await login(page, USERS.kitchen, '/staff')
  await expect(page.getByRole('heading', { name: "Today's Meals" })).toBeVisible()
  await expect(page.getByText('No meals scheduled for today')).toHaveCount(0)
  await page.getByRole('link', { name: 'Summary' }).click()
  await expect(page).toHaveURL(/\/staff\/kitchen\/summary$/)
  await expect(page.getByText("Today's delivery outcomes")).toBeVisible()
  await expect(page.getByText(/Total: \d+ meals/)).toBeVisible()
})

test('kitchen staff cannot open the delivery-only Completed page', async ({ page }) => {
  await login(page, USERS.kitchen, '/staff')
  await page.goto('/staff/completed')
  await expect(page).toHaveURL(/\/staff$/)
  await expect(page.getByRole('heading', { name: "Today's Meals" })).toBeVisible()
})
