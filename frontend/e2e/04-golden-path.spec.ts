import { expect, test } from '@playwright/test'
import { USERS, isoDate, login, modal, row, selectByText, tab, uniq } from './helpers'

/**
 * The core flow: customer → subscription (PENDING) → part payment → full payment →
 * ACTIVE + deliveries generated → delivery staff delivers it.
 */
test.describe.configure({ mode: 'serial' })

const u = uniq()
const CUSTOMER = `E2E Customer ${u}`
const PHONE = `9${String(Date.now()).slice(-9)}`
const PLAN = 'Weekly Breakfast' // seeded, ₹500

test.beforeEach(async ({ page }) => {
  await login(page, USERS.owner, '/app')
})

test('add a customer; duplicate phone is rejected', async ({ page }) => {
  await page.getByRole('link', { name: 'Customers' }).click()
  await page.getByRole('button', { name: 'Add Customer' }).click()
  await page.getByLabel('Name').fill(CUSTOMER)
  await page.getByLabel('Phone').fill(PHONE)
  await page.getByLabel('Email').fill(`e2e${u}@example.com`)
  await page.getByLabel('Address').fill('1 Test Lane, Pune')
  await page.getByLabel('Location').fill('Test Nagar')
  await page.getByRole('button', { name: 'Create' }).click()

  await page.getByPlaceholder(/Search by name/).fill(CUSTOMER)
  const r = row(page, CUSTOMER)
  await expect(r).toContainText(/CUST-\d+/)
  await expect(r).toContainText('ACTIVE')

  await page.getByRole('button', { name: 'Add Customer' }).click()
  await page.getByLabel('Name').fill('Phone Clash')
  await page.getByLabel('Phone').fill(PHONE)
  await page.getByRole('button', { name: 'Create' }).click()
  await expect(modal(page).getByText('A customer with this phone already exists.')).toBeVisible()
})

test('create a subscription → PENDING', async ({ page }) => {
  await page.getByRole('link', { name: 'Subscriptions' }).click()
  await page.getByRole('button', { name: 'New Subscription' }).click()
  await selectByText(page.getByLabel('Customer *'), CUSTOMER)
  await selectByText(page.getByLabel('Plan *'), PLAN)
  await page.getByLabel('Start Date *').fill(isoDate(0))
  await page.getByRole('button', { name: 'Create Subscription' }).click()

  await tab(page, 'Pending').click()
  const r = row(page, CUSTOMER)
  await expect(r).toContainText('PENDING')
  await expect(r).toContainText('₹500')
})

test('start date in the past is rejected', async ({ page }) => {
  await page.getByRole('link', { name: 'Subscriptions' }).click()
  await page.getByRole('button', { name: 'New Subscription' }).click()
  await selectByText(page.getByLabel('Customer *'), CUSTOMER)
  await selectByText(page.getByLabel('Plan *'), PLAN)
  await page.getByLabel('Start Date *').fill(isoDate(-1))
  await page.getByRole('button', { name: 'Create Subscription' }).click()
  await expect(modal(page).getByText('Start date cannot be in the past.')).toBeVisible()
})

test('part payment keeps it PENDING; overpayment is blocked', async ({ page }) => {
  await page.getByRole('link', { name: 'Payments' }).click()
  await page.getByRole('button', { name: 'Record Payment' }).click()
  await selectByText(page.getByLabel('Subscription *'), CUSTOMER)
  await page.getByLabel('Amount (₹) *').fill('200')
  await page.getByLabel('Method *').selectOption({ label: 'Cash' })
  await page.getByRole('button', { name: 'Record Payment' }).last().click()
  await expect(row(page, CUSTOMER).first()).toContainText('₹200')

  await page.getByRole('button', { name: 'Record Payment' }).click()
  await selectByText(page.getByLabel('Subscription *'), CUSTOMER)
  await page.getByLabel('Amount (₹) *').fill('400')
  await page.getByRole('button', { name: 'Record Payment' }).last().click()
  await expect(modal(page).getByText(/exceeds pending amount of ₹300/)).toBeVisible()
  await modal(page).getByRole('button', { name: 'Cancel' }).click()

  await page.getByRole('link', { name: 'Subscriptions' }).click()
  await tab(page, 'Pending').click()
  await expect(row(page, CUSTOMER)).toContainText('₹300') // still pending
})

test('full payment → ACTIVE, notification, delivery scheduled today', async ({ page }) => {
  await page.getByRole('link', { name: 'Payments' }).click()
  await page.getByRole('button', { name: 'Record Payment' }).click()
  await selectByText(page.getByLabel('Subscription *'), CUSTOMER)
  await page.getByLabel('Amount (₹) *').fill('300')
  await page.getByLabel('Method *').selectOption({ label: 'UPI' })
  await page.getByLabel('Transaction Reference').fill(`UPI-E2E-${u}`)
  await page.getByRole('button', { name: 'Record Payment' }).last().click()
  await expect(row(page, `UPI-E2E-${u}`)).toBeVisible()

  await page.getByRole('link', { name: 'Subscriptions' }).click()
  await tab(page, 'Active').click()
  await expect(row(page, CUSTOMER)).toContainText('ACTIVE')

  await page.reload()
  await page.locator('header button').filter({ has: page.locator('svg') }).first().click()
  await expect(page.getByText('Subscription Activated').first()).toBeVisible()

  await page.getByRole('link', { name: 'Deliveries' }).click()
  await expect(row(page, CUSTOMER)).toContainText('PENDING')
})

test('delivery staff marks it delivered; it shows under Completed', async ({ page }) => {
  await page.getByRole('button', { name: 'Logout' }).click()
  await login(page, USERS.delivery, '/staff')
  const r = row(page, CUSTOMER)
  await r.getByRole('button', { name: 'Delivered', exact: true }).click()
  await expect(r).toContainText('DELIVERED')
  await expect(r.getByRole('button')).toHaveCount(0)

  await page.getByRole('link', { name: 'Completed' }).click()
  await expect(row(page, CUSTOMER)).toContainText('DELIVERED')
})

test('pause → resume, cancel → renew', async ({ page }) => {
  await page.getByRole('link', { name: 'Subscriptions' }).click()
  await tab(page, 'Active').click()
  const active = row(page, CUSTOMER)
  await active.getByRole('button', { name: 'Pause' }).click()
  await tab(page, 'Paused').click()
  await row(page, CUSTOMER).getByRole('button', { name: 'Resume' }).click()
  await tab(page, 'Active').click()
  await expect(row(page, CUSTOMER)).toContainText('ACTIVE')

  // A second subscription for another seeded customer: cancel it, then renew
  await page.getByRole('button', { name: 'New Subscription' }).click()
  await selectByText(page.getByLabel('Customer *'), 'Anita Kulkarni')
  await selectByText(page.getByLabel('Plan *'), PLAN)
  await page.getByLabel('Start Date *').fill(isoDate(0))
  await page.getByRole('button', { name: 'Create Subscription' }).click()
  await tab(page, 'Pending').click()
  await row(page, 'Anita Kulkarni').getByRole('button', { name: 'Cancel' }).click()
  await tab(page, 'Cancelled').click()
  await row(page, 'Anita Kulkarni').getByRole('button', { name: 'Renew' }).click()
  await tab(page, 'Pending').click()
  await expect(row(page, 'Anita Kulkarni')).toContainText('PENDING')
})
