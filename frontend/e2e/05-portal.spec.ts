import { expect, test } from '@playwright/test'
import { USERS, field, isoDate, login, modal, row, tab } from './helpers'

/** Customer self-service: skip, pause (incl. rule violations), profile, renew. */

test('dashboard greets the customer with their plan', async ({ page }) => {
  await login(page, USERS.customer3, '/portal')
  await expect(page.getByText('Hello, Amit Deshmukh')).toBeVisible()
  await expect(page.getByText('Monthly Lunch').first()).toBeVisible()
  await expect(page.getByText('Days Remaining')).toBeVisible()
})

test('skip tomorrow\'s meal; past date is rejected', async ({ page }) => {
  await login(page, USERS.customer3, '/portal')
  await page.getByRole('link', { name: 'My Subscription' }).click()

  await page.getByRole('button', { name: /Skip Meal/ }).click()
  await field(modal(page), 'Date (optional — defaults to today)').fill(isoDate(-1))
  await modal(page).getByRole('button', { name: 'Skip Meal' }).click()
  await expect(page.getByText('Cannot skip a past date.')).toBeVisible()

  // The dialog stays open after an error — correct the date and retry
  await field(modal(page), 'Date (optional — defaults to today)').fill(isoDate(1))
  await field(modal(page), 'Reason (optional)').fill('E2E test')
  await modal(page).getByRole('button', { name: 'Skip Meal' }).click()
  await expect(page.getByText('Meal skipped successfully')).toBeVisible()

  await page.getByRole('link', { name: 'My Meals' }).click()
  await expect(row(page, isoDate(1))).toContainText(/SKIPPED/i)
})

test('future pause is scheduled: stays active, meals in range cancelled', async ({ page }) => {
  await login(page, USERS.customer3, '/portal')
  await page.getByRole('link', { name: 'My Subscription' }).click()
  await page.getByRole('button', { name: /Pause Subscription/ }).click()
  await field(modal(page), 'From').fill(isoDate(3))
  await field(modal(page), 'To (optional)').fill(isoDate(4))
  await modal(page).getByRole('button', { name: 'Pause' }).click()
  // Starts in 3 days, so the subscription stays ACTIVE until then (the nightly job flips it)
  await expect(page.getByText(`Pause scheduled from ${isoDate(3)}`)).toBeVisible()
  await expect(page.getByRole('button', { name: /Skip Meal/ })).toBeEnabled()

  await page.getByRole('link', { name: 'My Meals' }).click()
  await expect(row(page, isoDate(3))).toContainText(/CANCELLED/i)
})

test('pause longer than the business allows is rejected', async ({ page }) => {
  await login(page, USERS.customer4, '/portal')
  await page.getByRole('link', { name: 'My Subscription' }).click()
  await page.getByRole('button', { name: /Pause Subscription/ }).click()
  await field(modal(page), 'From').fill(isoDate(1))
  await field(modal(page), 'To (optional)').fill(isoDate(12))
  await modal(page).getByRole('button', { name: 'Pause' }).click()
  await expect(page.getByText('Maximum pause duration is 7 day(s).')).toBeVisible()
})

test('plan without pause rejects a pause request', async ({ page }) => {
  await login(page, USERS.customer1, '/portal') // Weekly Breakfast: pause not allowed
  await page.getByRole('link', { name: 'My Subscription' }).click()
  await page.getByRole('button', { name: /Pause Subscription/ }).click()
  await field(modal(page), 'From').fill(isoDate(1))
  await field(modal(page), 'To (optional)').fill(isoDate(2))
  await modal(page).getByRole('button', { name: 'Pause' }).click()
  await expect(page.getByText('Pausing is not allowed on this plan.')).toBeVisible()
})

test('payments are read-only and only the customer\'s own', async ({ page }) => {
  await login(page, USERS.customer3, '/portal')
  await page.getByRole('link', { name: 'Payments' }).click()
  await expect(page.getByRole('row')).not.toHaveCount(1) // header + at least one payment
  await expect(page.getByRole('button', { name: /Record/ })).toHaveCount(0)
})

test('profile: name locked, location editable', async ({ page }) => {
  await login(page, USERS.customer2, '/portal')
  await page.getByRole('link', { name: 'Profile' }).click()
  await expect(field(page, 'Name')).toBeDisabled()
  await field(page, 'Location / Landmark').fill('Near E2E Park')
  await page.getByRole('button', { name: 'Save Changes' }).click()
  await expect(page.getByText('Profile updated')).toBeVisible()
  await page.reload()
  await expect(field(page, 'Location / Landmark')).toHaveValue('Near E2E Park')
})

test('renew after the owner cancels', async ({ page, browser }) => {
  const owner = await (await browser.newContext()).newPage()
  await login(owner, USERS.owner, '/app')
  await owner.getByRole('link', { name: 'Subscriptions' }).click()
  await tab(owner, 'Active').click()
  await row(owner, 'Vikram Joshi').getByRole('button', { name: 'Cancel' }).click()
  await tab(owner, 'Cancelled').click()
  await expect(row(owner, 'Vikram Joshi')).toBeVisible()

  await login(page, USERS.customer5, '/portal')
  await page.getByRole('link', { name: 'My Subscription' }).click()
  await expect(page.getByRole('button', { name: /Skip Meal/ })).toBeDisabled()
  await page.getByRole('button', { name: /Renew/ }).click()
  await modal(page).getByRole('button', { name: 'Renew' }).click()
  await expect(page.getByText('Renewal requested')).toBeVisible()

  await tab(owner, 'Pending').click()
  await expect(row(owner, 'Vikram Joshi')).toContainText('PENDING')
})
