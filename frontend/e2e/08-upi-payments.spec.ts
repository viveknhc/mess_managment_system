import { expect, test, type Page } from '@playwright/test'
import { USERS, apiToken, confirmPopup, login, uniq } from './helpers'

/** UPI ID payments: owner sets a UPI ID → customer pays from the portal and taps "I've paid"
 * → owner confirms (subscription activates) or rejects (customer sees why and can pay again). */

const UPI_ID = 'e2emess@okicici'

/** A fresh customer with a portal login and an unpaid PENDING subscription. */
async function customerWithDue(page: Page) {
  const token = await apiToken(page, USERS.owner)
  const headers = { Authorization: `Bearer ${token}` }
  const u = uniq()
  const cust = await (await page.request.post('/api/v1/customers/', { data: { name: `UPI Payer ${u}` }, headers })).json()
  const creds = { username: `upi_${u}`, password: 'customer123' }
  expect((await page.request.post(`/api/v1/customers/${cust.id}/portal-login/`, { data: creds, headers })).ok()).toBeTruthy()
  const plans = await (await page.request.get('/api/v1/plans/', { headers })).json()
  const plan = plans.results[0]
  const sub = await page.request.post('/api/v1/subscriptions/', { data: { customer: cust.id, plan: plan.id }, headers })
  expect(sub.ok()).toBeTruthy()
  return { name: cust.name as string, creds, price: Number(plan.price) }
}

const inr = (n: number) => `₹${n.toLocaleString('en-IN')}`

test.describe.configure({ mode: 'serial' })

test('owner sets a UPI ID in Settings', async ({ page }) => {
  await login(page, USERS.owner, '/app')
  await page.getByRole('link', { name: 'Settings' }).click()
  await page.getByLabel('Your UPI ID').fill(UPI_ID)
  await page.getByRole('button', { name: 'Save Settings' }).click()
  await expect(page.getByText(/saved/i).first()).toBeVisible()

  // The guide opens from the ⓘ and covers both ways
  await page.getByRole('button', { name: 'How to collect payments online' }).click()
  await expect(page.getByRole('dialog').getByText('Option 1: UPI ID')).toBeVisible()
  await page.getByRole('button', { name: 'Got it' }).click()
})

test('customer pays by UPI, owner confirms, plan activates', async ({ page, browser }) => {
  const c = await customerWithDue(page)

  await login(page, c.creds, '/portal')
  await page.getByRole('button', { name: `Pay ${inr(c.price)}` }).first().click()
  const dialog = page.getByRole('dialog')
  await expect(dialog.getByText(`Pay ${inr(c.price)} by UPI`)).toBeVisible()
  await expect(dialog.getByText(UPI_ID)).toBeVisible()
  await expect(dialog.getByAltText(/UPI QR code/)).toBeVisible() // desktop viewport shows the QR
  await dialog.getByLabel(/UPI reference number/).fill('412345678901')
  await dialog.getByRole('button', { name: "I've paid" }).click()
  await expect(page.getByText(/Waiting for the mess to confirm/).first()).toBeVisible()

  const owner = await (await browser.newContext()).newPage()
  await login(owner, USERS.owner, '/app')
  await owner.getByRole('link', { name: 'Customer Payments' }).click()
  const panel = owner.locator('div', { has: owner.getByRole('heading', { name: /UPI payments to confirm/ }) }).last()
  const item = panel.getByRole('listitem').filter({ hasText: c.name })
  await expect(item).toContainText('412345678901')
  await item.getByRole('button', { name: 'Confirm' }).click()
  await confirmPopup(owner, 'Yes, I received it')
  await expect(owner.getByText('Payment recorded')).toBeVisible()
  await expect(owner.getByRole('row').filter({ hasText: c.name })).toContainText('UPI')

  await page.reload()
  await expect(page.getByText(/Waiting for the mess to confirm/)).toHaveCount(0)
  await expect(page.getByRole('button', { name: `Pay ${inr(c.price)}` })).toHaveCount(0)
})

test('owner rejects; customer sees the reason and can pay again', async ({ page, browser }) => {
  const c = await customerWithDue(page)

  await login(page, c.creds, '/portal')
  await page.getByRole('button', { name: `Pay ${inr(c.price)}` }).first().click()
  await page.getByRole('dialog').getByRole('button', { name: "I've paid" }).click()
  await expect(page.getByText(/Waiting for the mess to confirm/).first()).toBeVisible()

  const owner = await (await browser.newContext()).newPage()
  await login(owner, USERS.owner, '/app')
  await owner.getByRole('link', { name: 'Customer Payments' }).click()
  const item = owner.getByRole('listitem').filter({ hasText: c.name })
  await item.getByRole('button', { name: 'Reject' }).click()
  await owner.getByRole('dialog').getByRole('button', { name: 'Not received in my account' }).click()
  await confirmPopup(owner, 'Reject')
  await expect(owner.getByText('Payment rejected')).toBeVisible()

  await page.reload()
  await expect(page.getByText(/wasn't confirmed: Not received in my account/).first()).toBeVisible()
  await expect(page.getByRole('button', { name: `Pay ${inr(c.price)}` }).first()).toBeEnabled()
})
