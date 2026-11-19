/**
 * Screenshots for docs/user-guide.html — walks the app as every role, from onboarding a new
 * mess (super admin) to delivering a meal, and saves JPEGs to docs/user-guide/.
 *
 * Needs an ISOLATED backend with demo data (never your real DB) and the Vite dev server:
 *
 *   E2E_API_PORT=8077 E2E_DB_FILE=/tmp/guide.sqlite3 bash e2e/start-backend.sh &
 *   (cd ../backend && DATABASE_URL=sqlite:////tmp/guide.sqlite3 python3 manage.py seed_messes)
 *   VITE_PROXY_TARGET=http://localhost:8077 npx vite --port 5199 &
 *   node scripts/user-guide-screenshots.mjs            # GUIDE_URL defaults to http://localhost:5199
 *
 * Each step is independent: a failure is logged and the rest still run.
 */
import { mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium, devices } from 'playwright'

const BASE = process.env.GUIDE_URL ?? 'http://localhost:5199'
const OUT = join(dirname(fileURLToPath(import.meta.url)), '../../docs/user-guide')
mkdirSync(OUT, { recursive: true })

const DESKTOP = { viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1.25 }
const PHONE = { ...devices['Pixel 7'], deviceScaleFactor: 1.5 }

// The new mess the guide onboards, plus the seeded demo accounts (backend seed_data / seed_messes).
const NEW_MESS = {
  name: 'Shree Sai Mess',
  phone: '9876501234',
  email: 'hello@shreesaimess.in',
  address: 'Shop 4, FC Road, Pune',
  owner: 'Sai Prasad',
  ownerPhone: '9876501235',
  ownerEmail: 'sai@shreesaimess.in',
  username: 'shreesai',
  password: 'shreesai123',
}
const RIDER = { username: 'sai_rider', password: 'sairider123', name: 'Ravi Pawar' }
const USERS = {
  superadmin: ['superadmin', 'superadmin123'],
  owner: ['owner', 'owner123'],
  delivery: ['delivery1', 'delivery123'],
  kitchen: ['kitchen1', 'kitchen123'],
  customer: ['customer3', 'customer123'],
}

const failures = []
const browser = await chromium.launch()

async function newPage(opts = DESKTOP) {
  const page = await (await browser.newContext({ ...opts, timezoneId: 'Asia/Kolkata' })).newPage()
  page.setDefaultTimeout(15000)
  return page
}

/** `toasts: true` keeps notifications in the picture; otherwise leftovers from earlier steps are closed. */
async function shot(page, name, { full = false, locator, toasts = false } = {}) {
  if (!toasts) {
    for (const close of await page.locator('[data-sonner-toast] [data-close-button]').all()) {
      await close.click({ force: true }).catch(() => {})
    }
  }
  await page.waitForTimeout(500) // let toasts / popups finish animating
  const path = join(OUT, `${name}.jpg`)
  const opts = { path, type: 'jpeg', quality: 80 }
  if (locator) await locator.screenshot(opts)
  else await page.screenshot({ ...opts, fullPage: full })
  console.log('  ✓', name)
}

async function step(name, fn) {
  console.log(name)
  try {
    await fn()
  } catch (err) {
    failures.push(`${name}: ${err.message.split('\n')[0]}`)
    console.log('  ✗', err.message.split('\n')[0])
  }
}

async function login(page, [username, password], urlPart) {
  await page.goto(`${BASE}/login`)
  await page.getByLabel('Username').fill(username)
  await page.getByLabel('Password').fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.waitForURL(new RegExp(urlPart))
  await page.waitForLoadState('networkidle')
}

const modal = (page) => page.locator('div.fixed.inset-0').last()
const row = (page, text) => page.getByRole('row').filter({ hasText: text })
const isoDate = (offset = 0) => {
  const d = new Date()
  d.setDate(d.getDate() + offset)
  return d.toLocaleDateString('en-CA', { timeZone: 'Asia/Kolkata' })
}
async function selectByText(select, text) {
  const value = await select.locator('option', { hasText: text }).first().getAttribute('value')
  await select.selectOption(value)
}

// ── 1. Getting started ────────────────────────────────────────────────

await step('Login and forgot password', async () => {
  const page = await newPage()
  await page.goto(`${BASE}/login`)
  await shot(page, '01-login')
  await page.getByText('Forgot password?').click()
  await page.getByLabel('Username or email').fill('owner')
  await shot(page, '02-forgot-password')
  await page.getByRole('button', { name: 'Send reset link' }).click()
  await page.getByRole('status').waitFor()
  await shot(page, '03-reset-link-sent')
})

// ── 2. Super admin ───────────────────────────────────────────────────

const admin = await newPage()
await step('Super admin dashboard', async () => {
  await login(admin, USERS.superadmin, '/platform')
  await admin.getByText('Platform Overview').waitFor()
  await shot(admin, '10-admin-dashboard')
})

await step('MessDeck plans', async () => {
  await admin.getByRole('link', { name: 'Plans' }).click()
  await admin.getByRole('row').nth(1).waitFor()
  await shot(admin, '11-admin-plans')
  await admin.getByRole('row').filter({ has: admin.getByRole('cell', { name: 'Standard', exact: true }) })
    .getByRole('button', { name: 'Edit' }).click()
  await modal(admin).getByText('Features included').waitFor()
  await shot(admin, '12-admin-plan-form', { locator: modal(admin).locator('> div').last() })
  await modal(admin).getByRole('button', { name: 'Cancel' }).click()
})

await step('Add a new mess', async () => {
  await admin.getByRole('link', { name: 'Businesses' }).click()
  await admin.getByRole('row').nth(1).waitFor()
  await shot(admin, '13-admin-businesses')
  await admin.getByRole('button', { name: 'Add Business' }).click()
  const form = modal(admin)
  await form.getByPlaceholder('Business name').fill(NEW_MESS.name)
  await form.getByPlaceholder('Business phone').fill(NEW_MESS.phone)
  await form.getByPlaceholder('Business email').fill(NEW_MESS.email)
  await form.getByPlaceholder('Address').fill(NEW_MESS.address)
  await form.getByPlaceholder('Owner name').fill(NEW_MESS.owner)
  await form.getByPlaceholder('Owner phone').fill(NEW_MESS.ownerPhone)
  await form.getByPlaceholder('Owner email').fill(NEW_MESS.ownerEmail)
  await form.getByPlaceholder('Owner username').fill(NEW_MESS.username)
  await form.getByPlaceholder('Owner password (min 8)').fill(NEW_MESS.password)
  await shot(admin, '14-admin-add-mess')
  await form.getByRole('button', { name: 'Create Business' }).click()
  await row(admin, NEW_MESS.name).waitFor()
  await shot(admin, '15-admin-mess-created')
})

await step('Record the first payment', async () => {
  await row(admin, NEW_MESS.name).getByRole('button', { name: 'Record Payment' }).click()
  await modal(admin).getByRole('heading', { name: 'Record Payment' }).waitFor()
  await shot(admin, '16-admin-record-payment')
  await modal(admin).getByRole('button', { name: /Record/ }).last().click()
  await admin.getByText(/Payment of .* recorded/).waitFor()
  await shot(admin, '17-admin-payment-recorded', { toasts: true })
})

await step('Customize the mess', async () => {
  await row(admin, NEW_MESS.name).getByRole('button', { name: 'Customize' }).click()
  await admin.getByText('Workflows').waitFor()
  await shot(admin, '18-admin-customize')
  await admin.getByRole('button', { name: 'Close', exact: true }).click()
})

await step('Mess details', async () => {
  await admin.getByRole('link', { name: 'Mess Details' }).click()
  await admin.getByRole('navigation', { name: 'Messes' }).getByText('Green Valley Hostel Mess').click()
  await admin.locator('main h1', { hasText: 'Green Valley' }).waitFor()
  await admin.getByText('MessDeck plan & billing').waitFor()
  await shot(admin, '19-admin-mess-details')
})

await step('Billing payments and suspend', async () => {
  await admin.getByRole('link', { name: 'Payments' }).click()
  await admin.getByRole('row').nth(1).waitFor()
  await shot(admin, '20-admin-payments')
  await admin.getByRole('link', { name: 'Businesses' }).click()
  await row(admin, 'Sharma Tiffin Service').getByRole('button', { name: 'Suspend' }).click()
  await admin.getByRole('dialog').waitFor()
  await shot(admin, '21-admin-suspend-confirm')
  await admin.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click()
})

// ── 3. Owner: setting up the new mess ────────────────────────────────

const own = await newPage()
const CUSTOMER = { name: 'Anita Kulkarni', phone: '9822012345', email: 'anita@example.com', address: 'B-12, Shivaji Nagar, Pune', location: 'Shivaji Nagar' }
const PLAN = { name: 'Monthly Lunch', days: '30', meals: '30', price: '2400' }

await step('Owner first login', async () => {
  await login(own, [NEW_MESS.username, NEW_MESS.password], '/app')
  await own.getByText('Quick Actions').waitFor()
  await shot(own, '30-owner-first-dashboard')
})

await step('Business profile and settings', async () => {
  await own.getByRole('link', { name: 'Business Profile' }).click()
  await own.waitForLoadState('networkidle')
  await shot(own, '31-owner-business-profile')
  await own.getByRole('link', { name: 'Settings' }).click()
  await own.getByRole('button', { name: 'Save Settings' }).waitFor()
  await shot(own, '32-owner-settings', { full: true })
})

await step('Meals', async () => {
  await own.getByRole('link', { name: 'Meals' }).click()
  await own.getByRole('row').nth(1).waitFor()
  await shot(own, '33-owner-meals')
})

await step('Add a meal plan', async () => {
  await own.getByRole('link', { name: 'Plans' }).click()
  await own.getByRole('button', { name: 'Add Plan' }).click()
  const m = modal(own)
  await m.getByLabel('Name').fill(PLAN.name)
  await m.getByLabel('Meal Type').selectOption({ label: 'Lunch' })
  await m.getByLabel('Days').fill(PLAN.days)
  await m.getByLabel('Meals').fill(PLAN.meals)
  await m.getByLabel('Price (₹) *').fill(PLAN.price)
  await m.getByLabel('Allow skip').check()
  await m.getByLabel('Allow pause').check()
  await shot(own, '34-owner-add-plan')
  await m.getByRole('button', { name: 'Create' }).click()
  await row(own, PLAN.name).waitFor()
  await shot(own, '35-owner-plans')
})

await step('Add a customer', async () => {
  await own.getByRole('link', { name: 'Customers' }).click()
  await own.getByRole('button', { name: 'Add Customer' }).click()
  await own.getByLabel('Name').fill(CUSTOMER.name)
  await own.getByLabel('Phone').fill(CUSTOMER.phone)
  await own.getByLabel('Email').fill(CUSTOMER.email)
  await own.getByLabel('Address').fill(CUSTOMER.address)
  await own.getByLabel('Location').fill(CUSTOMER.location)
  await shot(own, '36-owner-add-customer')
  await own.getByRole('button', { name: 'Create' }).click()
  await row(own, CUSTOMER.name).waitFor()
  await shot(own, '37-owner-customers')
})

await step('Start a subscription', async () => {
  await own.getByRole('link', { name: 'Subscriptions' }).click()
  await own.getByRole('button', { name: 'New Subscription' }).click()
  await selectByText(own.getByLabel('Customer *'), CUSTOMER.name)
  await selectByText(own.getByLabel('Plan *'), PLAN.name)
  await own.getByLabel('Start Date *').fill(isoDate(0))
  await shot(own, '38-owner-new-subscription')
  await own.getByRole('button', { name: 'Create Subscription' }).click()
  await row(own, CUSTOMER.name).waitFor()
  await shot(own, '39-owner-subscription-pending')
})

await step('Record the customer payment', async () => {
  await own.getByRole('link', { name: 'Customer Payments' }).click()
  await own.getByRole('button', { name: 'Record Payment' }).click()
  await selectByText(own.getByLabel('Subscription *'), CUSTOMER.name)
  await own.getByLabel('Amount (₹) *').fill(PLAN.price)
  await own.getByLabel('Method *').selectOption({ label: 'UPI' })
  await own.getByLabel('Transaction Reference').fill('UPI-4471209')
  await shot(own, '40-owner-record-payment')
  await own.getByRole('button', { name: 'Record Payment' }).last().click()
  await own.getByText(/Payment of .* recorded/).waitFor()
  await shot(own, '41-owner-payment-recorded', { toasts: true })
  await own.getByRole('link', { name: 'Subscriptions' }).click()
  await row(own, CUSTOMER.name).filter({ hasText: 'ACTIVE' }).waitFor()
  await shot(own, '42-owner-subscription-active')
})

await step('Add delivery staff', async () => {
  await own.getByRole('link', { name: 'Staff' }).click()
  await own.getByRole('button', { name: 'Add Staff' }).click()
  await own.getByLabel('Username').fill(RIDER.username)
  await own.getByLabel('Full Name').fill(RIDER.name)
  await own.getByLabel('Role').selectOption({ label: 'Delivery Staff' })
  await own.getByLabel('Password').fill(RIDER.password)
  await shot(own, '43-owner-add-staff')
  await own.getByRole('button', { name: 'Create' }).click()
  await row(own, RIDER.username).waitFor()
  await shot(own, '44-owner-staff')
})

await step('Owner deliveries (new mess)', async () => {
  await own.getByRole('link', { name: 'Deliveries' }).click()
  await row(own, CUSTOMER.name).waitFor()
  await shot(own, '45-owner-deliveries')
})

await step('MessDeck billing', async () => {
  await own.getByRole('link', { name: 'MessDeck Billing' }).click()
  await own.waitForLoadState('networkidle')
  await shot(own, '46-owner-billing', { full: true })
})

// ── 4. Owner: a busy mess (demo data) ────────────────────────────────

const busy = await newPage()
await step('Busy dashboard and notifications', async () => {
  await login(busy, USERS.owner, '/app')
  await busy.getByText('Expiring Subscriptions').waitFor()
  await shot(busy, '50-owner-dashboard', { full: true })
  await busy.locator('header button').filter({ has: busy.locator('svg') }).first().click()
  await busy.waitForTimeout(500)
  await shot(busy, '51-owner-notifications')
  await busy.keyboard.press('Escape')
  await busy.mouse.click(10, 790)
})

await step('Customer details', async () => {
  await busy.getByRole('link', { name: 'Customers' }).click()
  await busy.getByRole('row').nth(1).waitFor()
  await shot(busy, '52-owner-customers-list')
  await row(busy, 'Amit Deshmukh').first().click() // rows open the customer's page
  await busy.waitForLoadState('networkidle')
  await shot(busy, '53-owner-customer-details', { full: true })
})

await step('Subscriptions tabs', async () => {
  await busy.getByRole('link', { name: 'Subscriptions' }).click()
  await busy.getByRole('row').nth(1).waitFor()
  await shot(busy, '54-owner-subscriptions')
  await row(busy, 'ACTIVE').first().getByRole('button', { name: 'Cancel' }).click()
  await busy.getByRole('dialog').waitFor()
  await shot(busy, '55-owner-cancel-confirm')
  await busy.getByRole('dialog').getByRole('button', { name: 'Keep it' }).click()
})

await step('Owner deliveries actions', async () => {
  await busy.getByRole('link', { name: 'Deliveries' }).click()
  await busy.getByRole('row').nth(1).waitFor()
  await shot(busy, '56-owner-deliveries-busy')
  const pending = row(busy, 'PENDING').first()
  await pending.getByRole('button', { name: 'Skip', exact: true }).click()
  await busy.getByRole('dialog').waitFor()
  await shot(busy, '57-owner-skip-confirm')
  await busy.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click()
})

await step('Reports', async () => {
  await busy.getByRole('link', { name: 'Reports' }).click()
  await busy.getByText('Revenue Trend').waitFor()
  await busy.waitForTimeout(800)
  await shot(busy, '58-owner-reports', { full: true })
})

await step('Help & support', async () => {
  await busy.getByRole('link', { name: 'Help & Support' }).click()
  await busy.waitForLoadState('networkidle')
  await shot(busy, '59-owner-help')
})

// ── 5. Delivery staff (phone) ────────────────────────────────────────

await step('Delivery staff run', async () => {
  const page = await newPage(PHONE)
  await login(page, USERS.delivery, '/staff')
  await page.getByRole('button', { name: 'Delivered', exact: true }).first().waitFor()
  await shot(page, '60-delivery-home')
  const name = await page.locator('main li p.text-lg').first().innerText()
  await page.getByRole('button', { name: 'Delivered', exact: true }).first().click()
  await page.getByText(`Delivered to ${name}`).waitFor()
  await shot(page, '61-delivery-delivered-toast', { toasts: true })
  await page.getByRole('button', { name: /^Not delivered to / }).first().click()
  await page.getByRole('dialog').waitFor()
  await page.getByRole('dialog').getByRole('button', { name: 'Door locked' }).click()
  await shot(page, '62-delivery-not-delivered')
  await page.getByRole('dialog').getByRole('button', { name: 'Mark not delivered' }).click()
  await page.getByText(/^Marked not delivered/).waitFor()
  await page.getByRole('tab', { name: /Done/ }).click()
  await shot(page, '63-delivery-done-tab')
})

await step('New rider sees the new mess', async () => {
  const page = await newPage(PHONE)
  await login(page, [RIDER.username, RIDER.password], '/staff')
  await page.getByText(CUSTOMER.name).waitFor()
  await shot(page, '64-delivery-new-mess')
})

// ── 6. Kitchen staff (phone) ─────────────────────────────────────────

await step('Kitchen', async () => {
  const page = await newPage(PHONE)
  await login(page, USERS.kitchen, '/staff')
  await page.getByRole('heading', { name: "Today's Meals" }).waitFor()
  await shot(page, '70-kitchen-meals')
  await page.getByRole('link', { name: 'Summary' }).click()
  await page.waitForLoadState('networkidle')
  await shot(page, '71-kitchen-summary')
})

// ── 7. Customer portal (phone) ───────────────────────────────────────

await step('Customer portal', async () => {
  const page = await newPage(PHONE)
  await login(page, USERS.customer, '/portal')
  await page.getByText('Days Remaining').waitFor()
  await shot(page, '80-customer-dashboard', { full: true })
  await page.getByRole('link', { name: 'My Subscription' }).click()
  await page.getByRole('button', { name: /Skip Meal/ }).waitFor()
  await shot(page, '81-customer-subscription', { full: true })
  await page.getByRole('button', { name: /Skip Meal/ }).click()
  await modal(page).getByRole('button', { name: 'Skip Meal' }).waitFor()
  await shot(page, '82-customer-skip')
  await modal(page).getByRole('button', { name: 'Cancel' }).click()
  await page.getByRole('button', { name: /Pause Subscription/ }).click()
  await modal(page).getByRole('button', { name: 'Pause' }).waitFor()
  await shot(page, '83-customer-pause')
  await modal(page).getByRole('button', { name: 'Cancel' }).click()
  await page.getByRole('link', { name: 'My Meals' }).click()
  await page.waitForLoadState('networkidle')
  await shot(page, '84-customer-meals')
  await page.getByRole('link', { name: 'Payments' }).click()
  await page.waitForLoadState('networkidle')
  await shot(page, '85-customer-payments')
  await page.getByRole('link', { name: 'Profile' }).click()
  await page.waitForLoadState('networkidle')
  await shot(page, '86-customer-profile')
})

await browser.close()
if (failures.length) {
  console.log(`\n${failures.length} step(s) failed:\n- ${failures.join('\n- ')}`)
  process.exit(1)
}
console.log('\nAll screenshots saved to', OUT)
