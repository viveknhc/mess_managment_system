import { expect, test } from '@playwright/test'
import { USERS, field, login, logout, modal, row, uniq } from './helpers'

/** Owner configures the business: meals, plans, staff, settings, profile. Manager restrictions. */
const u = uniq()

test.beforeEach(async ({ page }) => {
  await login(page, USERS.owner, '/app')
})

test('dashboard shows KPIs and widgets', async ({ page }) => {
  for (const label of ['Active Customers', 'Active Subscriptions', "Today's Revenue", 'Pending Payments']) {
    await expect(page.getByText(label).first()).toBeVisible()
  }
  await expect(page.getByText('Expiring Subscriptions')).toBeVisible()
  await expect(page.getByText('Quick Actions')).toBeVisible()
})

test('add a meal, then deactivate and reactivate it', async ({ page }) => {
  const meal = `E2E Tiffin ${u}`
  await page.getByRole('link', { name: 'Meals' }).click()
  await page.getByRole('button', { name: 'Add Meal' }).click()
  await page.getByLabel('Name').fill(meal)
  await page.getByLabel('Description').fill('Light evening snack box')
  await page.getByLabel('Price (₹)').fill('60')
  await page.getByRole('button', { name: 'Create' }).click()

  const r = row(page, meal)
  await expect(r).toContainText('₹60.00')
  await expect(r).toContainText('Active')
  await r.getByRole('button', { name: 'Deactivate' }).click()
  await expect(r).toContainText('Inactive')
  await r.getByRole('button', { name: 'Activate' }).click()
  await expect(r).toContainText('Active')
})

test('create a subscription plan with skip + pause', async ({ page }) => {
  const plan = `E2E Weekly Lunch ${u}`
  await page.getByRole('link', { name: 'Plans' }).click()
  await page.getByRole('button', { name: 'Add Plan' }).click()
  const m = modal(page)
  await m.getByLabel('Name').fill(plan)
  await m.getByLabel('Meal Type').selectOption({ label: 'Lunch' })
  await m.getByLabel('Days').fill('7')
  await m.getByLabel('Meals').fill('7')
  await m.getByLabel('Price (₹) *').fill('700')
  await m.getByLabel('Allow skip').check()
  await m.getByLabel('Allow pause').check()
  await m.getByRole('button', { name: 'Create' }).click()

  const r = row(page, plan)
  await expect(r).toContainText('Lunch')
  await expect(r).toContainText('₹700')
  await expect(r).toContainText('Skip')
  await expect(r).toContainText('Pause')
})

test('add delivery staff who can then log in', async ({ page, browser }) => {
  const username = `e2erider${u}`
  await page.getByRole('link', { name: 'Staff' }).click()
  await page.getByRole('button', { name: 'Add Staff' }).click()
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Full Name').fill(`E2E Rider ${u}`)
  await page.getByLabel('Role').selectOption({ label: 'Delivery Staff' })
  await page.getByLabel('Password').fill('e2erider123')
  await page.getByRole('button', { name: 'Create' }).click()
  await expect(row(page, `@${username}`)).toContainText('Delivery')

  const rider = await (await browser.newContext()).newPage()
  await login(rider, { username, password: 'e2erider123' }, '/staff')
  await expect(rider.getByText("Today's Deliveries").first()).toBeVisible()
})

test('settings: change max pause days, persists after reload, then restore', async ({ page }) => {
  await page.getByRole('link', { name: 'Settings' }).click()
  const maxPause = field(page, 'Max Pause Days')
  await expect(maxPause).toHaveValue('7')
  await maxPause.fill('6')
  await page.getByRole('button', { name: 'Save Settings' }).click()
  await expect(page.getByText('Settings saved')).toBeVisible()
  await page.reload()
  await expect(field(page, 'Max Pause Days')).toHaveValue('6')
  await field(page, 'Max Pause Days').fill('7')
  await page.getByRole('button', { name: 'Save Settings' }).click()
  await expect(page.getByText('Settings saved')).toBeVisible()
})

test('edit business profile', async ({ page }) => {
  await page.getByRole('link', { name: 'Business Profile' }).click()
  await page.getByRole('button', { name: 'Edit' }).click()
  await field(page, 'Phone').fill('020-25559999')
  await page.getByRole('button', { name: 'Save Changes' }).click()
  await expect(page.getByText('Business profile updated successfully')).toBeVisible()
  await expect(page.getByText('020-25559999')).toBeVisible()
})

test('manager cannot manage staff or settings', async ({ page }) => {
  await logout(page)
  await login(page, USERS.manager, '/app')
  await page.getByRole('link', { name: 'Staff' }).click()
  await expect(row(page, '@delivery1')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Add Staff' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Deactivate' })).toHaveCount(0)
  await page.getByRole('link', { name: 'Settings' }).click()
  await expect(field(page, 'Max Pause Days')).toBeDisabled()
})
