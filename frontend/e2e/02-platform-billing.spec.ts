import { expect, test } from '@playwright/test'
import { USERS, apiToken, login, logout, row, uniq } from './helpers'

/**
 * Platform admin creates a SaaS plan → a new business signs up (trial) → buys the plan →
 * hits the plan's customer quota → platform admin suspends and reactivates it.
 */
test.describe.configure({ mode: 'serial' })

const u = uniq()
const PLAN = `E2E Starter ${u}`
const BIZ = `E2E Tiffins ${u}`
const OWNER = { username: `e2eowner${u}`, password: 'e2eowner123' }

test('platform admin creates a SaaS plan', async ({ page }) => {
  await login(page, USERS.superadmin, '/platform')
  await expect(page.getByText('Platform Overview')).toBeVisible()

  await page.getByRole('link', { name: 'Plans' }).click()
  await page.getByRole('button', { name: 'Add Plan' }).click()
  await page.getByPlaceholder('Plan name').fill(PLAN)
  await page.getByPlaceholder('Monthly price').fill('499')
  await page.getByPlaceholder('Max customers (0=unlimited)').fill('2')
  await page.getByPlaceholder('Max staff (0=unlimited)').fill('1')
  await page.getByPlaceholder('Features (one per line)').fill('Up to 2 customers\nEmail support')
  await page.getByRole('button', { name: 'Create', exact: true }).click()

  const planRow = row(page, PLAN)
  await expect(planRow).toBeVisible()
  await expect(planRow).toContainText('499')
})

test('new business signs up from the landing page and gets a trial', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'Start Free Trial' }).first().click()
  await expect(page).toHaveURL(/\/signup$/)

  await page.getByPlaceholder("e.g. Rahul's Mess").fill(BIZ)
  await page.getByPlaceholder('Rahul Kumar').fill('E2E Owner')
  await page.getByPlaceholder('9876543210').fill('9000000000')
  await page.getByPlaceholder('rahul@example.com').fill(`owner${u}@example.com`)
  await page.getByPlaceholder('rahul', { exact: true }).fill(OWNER.username)
  await page.getByPlaceholder('Min 8 characters').fill(OWNER.password)
  await page.getByRole('button', { name: 'Start Free Trial' }).click()

  await expect(page).toHaveURL(/\/app$/)
  await expect(page.getByText(BIZ).first()).toBeVisible()

  // Signup seeds the four default meals
  await page.getByRole('link', { name: 'Meals' }).click()
  for (const meal of ['Breakfast', 'Lunch', 'Dinner', 'Snacks']) {
    await expect(row(page, meal)).toBeVisible()
  }

  await page.getByRole('link', { name: 'Billing' }).click()
  await expect(page.getByText('TRIAL', { exact: true })).toBeVisible()
  await expect(page.getByText('Free Trial')).toBeVisible()
})

test('owner subscribes to the plan (dev mode activates instantly)', async ({ page }) => {
  await login(page, OWNER, '/app')
  await page.getByRole('link', { name: 'Billing' }).click()
  const card = page.locator('div').filter({ has: page.getByText(PLAN, { exact: true }) }).filter({ has: page.getByRole('button', { name: 'Subscribe' }) }).last()
  await card.getByRole('button', { name: 'Subscribe' }).click()
  await expect(page.getByText('ACTIVE', { exact: true })).toBeVisible()
  await expect(page.getByText('Current Plan').nth(1)).toBeVisible()
})

test('plan quota blocks the 3rd customer', async ({ page }) => {
  await login(page, OWNER, '/app')
  const token = await apiToken(page, OWNER)
  for (const name of ['Quota One', 'Quota Two']) {
    const res = await page.request.post('/api/v1/customers/', { data: { name }, headers: { Authorization: `Bearer ${token}` } })
    expect(res.status()).toBe(201)
  }
  await page.getByRole('link', { name: 'Customers' }).click()
  await page.getByRole('button', { name: 'Add Customer' }).click()
  await page.getByLabel('Name').fill('Quota Three')
  await page.getByRole('button', { name: 'Create' }).click()
  await expect(page.getByText('Your plan allows a maximum of 2 customers. Please upgrade your plan.')).toBeVisible()
})

test('businesses only see their own data', async ({ page }) => {
  await login(page, OWNER, '/app')
  await page.getByRole('link', { name: 'Customers' }).click()
  await expect(row(page, 'Quota One')).toBeVisible()
  await page.getByPlaceholder(/Search by name/).fill('Rahul')
  await expect(page.getByText('No customers match your search')).toBeVisible()
})

test('platform admin suspends the business → owner is blocked → reactivate', async ({ browser }) => {
  const admin = await (await browser.newContext()).newPage()
  await login(admin, USERS.superadmin, '/platform')
  await admin.getByRole('link', { name: 'Businesses' }).click()
  admin.once('dialog', (d) => d.accept())
  await row(admin, BIZ).getByRole('button', { name: 'Suspend' }).click()
  await expect(row(admin, BIZ)).toContainText('SUSPENDED')

  const owner = await (await browser.newContext()).newPage()
  await login(owner, OWNER, '/app')
  await expect(owner.getByText('Your business account is suspended.', { exact: false })).toBeVisible()
  const res = await owner.request.get('/api/v1/customers/', { headers: { Authorization: `Bearer ${await apiToken(owner, OWNER)}` } })
  expect(res.status()).toBe(403)

  await row(admin, BIZ).getByRole('button', { name: 'Reactivate' }).click()
  await expect(row(admin, BIZ)).toContainText('ACTIVE')

  await owner.reload()
  await expect(owner.getByText('Your business account is suspended.', { exact: false })).toBeHidden()
  await logout(owner)
})
