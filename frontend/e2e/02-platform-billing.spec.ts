import { expect, test } from '@playwright/test'
import { USERS, apiToken, login, logout, modal, row, uniq } from './helpers'

/**
 * Monthly plan billing (docs/Monthly_Subscription_Plan.pdf) — no self-signup, no trial, no online checkout:
 * platform admin adds a business → ₹3,000 first payment due → admin records it (UPI/cash) → ACTIVE, paid until
 * a month out, ₹500/month next → suspend/reactivate (refused while money is owed) → owner cancels.
 */
test.describe.configure({ mode: 'serial' })

const u = uniq()
const PLAN = `E2E Plan ${u}`
const BIZ = `E2E Mess ${u}`
const OWNER = { username: `e2eowner${u}`, password: 'e2eowner123' }
const UNPAID_BIZ = `E2E Unpaid Mess ${u}`

test('platform admin creates a SaaS plan with setup and reactivation fees', async ({ page }) => {
  await login(page, USERS.superadmin, '/platform')
  await expect(page.getByText('Platform Overview')).toBeVisible()

  await page.getByRole('link', { name: 'Plans' }).click()
  await page.getByRole('button', { name: 'Add Plan' }).click()
  await page.getByPlaceholder('Plan name').fill(PLAN)
  await page.getByPlaceholder('Monthly price').fill('500')
  await page.getByPlaceholder('Setup fee').fill('2500')
  await page.getByPlaceholder('Reactivation fee').fill('1000')
  await page.getByRole('button', { name: 'Create', exact: true }).click()

  const planRow = row(page, PLAN)
  await expect(planRow).toBeVisible()
  await expect(planRow).toContainText('2500')
  await expect(planRow).toContainText('1000')
})

test('platform admin adds a business — first payment of ₹3,000 is due', async ({ page }) => {
  await login(page, USERS.superadmin, '/platform')
  await page.getByRole('link', { name: 'Businesses' }).click()
  await page.getByRole('button', { name: 'Add Business' }).click()

  const form = modal(page)
  await form.getByPlaceholder('Business name').fill(BIZ)
  await form.getByPlaceholder('Owner name').fill('E2E Owner')
  await form.getByPlaceholder('Owner username').fill(OWNER.username)
  await form.getByPlaceholder('Owner password (min 8)').fill(OWNER.password)
  await form.getByRole('button', { name: 'Create Business' }).click()

  const bizRow = row(page, BIZ)
  await expect(bizRow).toContainText('Awaiting first payment')
  await expect(bizRow).toContainText('₹3,000')
})

test('owner sees the first payment breakdown on the Billing page', async ({ page }) => {
  await login(page, OWNER, '/app')

  // New businesses get the four default meals
  await page.getByRole('link', { name: 'Meals' }).click()
  for (const meal of ['Breakfast', 'Lunch', 'Dinner', 'Tiffin']) {
    await expect(row(page, meal)).toBeVisible()
  }

  await page.getByRole('link', { name: 'Billing' }).click()
  await expect(page.getByText('Awaiting first payment')).toBeVisible()
  await expect(page.getByText('One-time setup fee')).toBeVisible()
  await expect(page.getByText('₹3,000').first()).toBeVisible()
  await expect(page.getByText('No payments yet.')).toBeVisible()
})

test('platform admin records the first payment — wrong amount is rejected', async ({ page }) => {
  await login(page, USERS.superadmin, '/platform')
  await page.getByRole('link', { name: 'Businesses' }).click()
  await row(page, BIZ).getByRole('button', { name: 'Record Payment' }).click()

  const form = modal(page)
  await form.getByLabel('Amount received').fill('500')
  await form.getByRole('button', { name: 'Record Payment' }).click()
  await expect(form.getByText('Amount due is ₹3000.00. Record exactly that amount.')).toBeVisible()

  await form.getByLabel('Amount received').fill('3000')
  await form.getByLabel('Reference (optional)').fill(`UPI-${u}`)
  await form.getByRole('button', { name: 'Record Payment' }).click()

  const bizRow = row(page, BIZ)
  await expect(bizRow).toContainText('Active')
  await expect(bizRow).toContainText('₹500')
  // Paid Until column is filled in once the first month is paid
  await expect(bizRow.getByRole('cell').nth(4)).not.toHaveText('—')
})

test('owner sees the plan is active and the payment history', async ({ page }) => {
  await login(page, OWNER, '/app')
  await page.getByRole('link', { name: 'Billing' }).click()
  await expect(page.getByText('Active', { exact: true })).toBeVisible()
  await expect(page.getByText('Paid until', { exact: true })).toBeVisible()
  await expect(page.getByText('Not paid yet')).toHaveCount(0)
  await expect(page.getByText(/You're paid until .+\. Next payment of ₹500 is due on/)).toBeVisible()
  await expect(page.getByText('incl. ₹2,500 setup')).toBeVisible()
})

test('businesses only see their own data', async ({ page }) => {
  await login(page, OWNER, '/app')
  const token = await apiToken(page, OWNER)
  const res = await page.request.post('/api/v1/customers/', { data: { name: `Own Customer ${u}` }, headers: { Authorization: `Bearer ${token}` } })
  expect(res.status()).toBe(201)
  await page.getByRole('link', { name: 'Customers' }).click()
  await expect(row(page, `Own Customer ${u}`)).toBeVisible()
  await page.getByPlaceholder(/Search by name/).fill('Rahul')
  await expect(page.getByText('No customers match your search')).toBeVisible()
})

test('platform admin suspends the business → owner is blocked → reactivate', async ({ browser }) => {
  const admin = await (await browser.newContext()).newPage()
  await login(admin, USERS.superadmin, '/platform')
  await admin.getByRole('link', { name: 'Businesses' }).click()
  admin.once('dialog', (d) => d.accept())
  await row(admin, BIZ).getByRole('button', { name: 'Suspend' }).click()
  await expect(row(admin, BIZ)).toContainText('Suspended')

  const owner = await (await browser.newContext()).newPage()
  await login(owner, OWNER, '/app')
  await expect(owner.getByText('Your business account is suspended.', { exact: false })).toBeVisible()
  // Suspended owners are sent to Billing (the only business API the backend still serves)
  await expect(owner).toHaveURL(/\/app\/billing$/)
  const res = await owner.request.get('/api/v1/customers/', { headers: { Authorization: `Bearer ${await apiToken(owner, OWNER)}` } })
  expect(res.status()).toBe(403)

  admin.once('dialog', (d) => d.accept())
  await row(admin, BIZ).getByRole('button', { name: 'Reactivate' }).click()
  await expect(row(admin, BIZ)).toContainText('Active')

  await owner.reload()
  await expect(owner.getByText('Your business account is suspended.', { exact: false })).toBeHidden()
  await logout(owner)
})

test('reactivate is refused while money is owed — admin must record a payment', async ({ page }) => {
  await login(page, USERS.superadmin, '/platform')
  await page.getByRole('link', { name: 'Businesses' }).click()
  await page.getByRole('button', { name: 'Add Business' }).click()
  const form = modal(page)
  await form.getByPlaceholder('Business name').fill(UNPAID_BIZ)
  await form.getByPlaceholder('Owner username').fill(`e2eunpaid${u}`)
  await form.getByPlaceholder('Owner password (min 8)').fill('e2eunpaid123')
  await form.getByRole('button', { name: 'Create Business' }).click()

  page.once('dialog', (d) => d.accept())
  await row(page, UNPAID_BIZ).getByRole('button', { name: 'Suspend' }).click()
  await expect(row(page, UNPAID_BIZ)).toContainText('Suspended')

  page.once('dialog', (d) => d.accept())
  await row(page, UNPAID_BIZ).getByRole('button', { name: 'Reactivate' }).click()
  await expect(page.getByRole('alert')).toContainText(/Record the payment/i)
  await expect(row(page, UNPAID_BIZ)).toContainText('Suspended')
})

test('owner cancels the monthly plan and keeps access until the paid month ends', async ({ page }) => {
  await login(page, OWNER, '/app')
  await page.getByRole('link', { name: 'Billing' }).click()
  page.once('dialog', (d) => d.accept())
  await page.getByRole('button', { name: 'Cancel monthly plan' }).click()
  await expect(page.getByText('Cancelled', { exact: true })).toBeVisible()
  await expect(page.getByText(/You can keep using MessDeck until/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Cancel monthly plan' })).toHaveCount(0)
})
