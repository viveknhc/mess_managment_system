import { expect, test, type Page } from '@playwright/test'
import { USERS, login, rupees, tab } from './helpers'

/** Sortable DataTable: asc → desc → off, server-side sort across pages, rows-per-page. */

test.beforeEach(async ({ page }) => {
  await login(page, USERS.owner, '/app')
})

const header = (page: Page, name: string) => page.getByRole('columnheader', { name })
const columnTexts = async (page: Page, index: number) =>
  page.locator('tbody tr').evaluateAll((rows, i) => rows.map((r) => (r.children[i] as HTMLElement)?.innerText ?? ''), index)

test('header click cycles ascending → descending → off', async ({ page }) => {
  await page.getByRole('link', { name: 'Customers' }).click()
  const h = header(page, 'Name')
  await expect(h).not.toHaveAttribute('aria-sort')
  await h.getByRole('button').click()
  await expect(h).toHaveAttribute('aria-sort', 'ascending')
  await h.getByRole('button').click()
  await expect(h).toHaveAttribute('aria-sort', 'descending')
  await h.getByRole('button').click()
  await expect(h).not.toHaveAttribute('aria-sort')
})

test('customer names sort A→Z and Z→A', async ({ page }) => {
  await page.getByRole('link', { name: 'Customers' }).click()
  await page.getByLabel('Rows').selectOption('50')
  const names = () => columnTexts(page, 1)
  const cmp = (a: string, b: string) => a.localeCompare(b, undefined, { sensitivity: 'base' })

  await header(page, 'Name').getByRole('button').click()
  await expect(header(page, 'Name')).toHaveAttribute('aria-sort', 'ascending')
  await expect.poll(async () => { const n = await names(); return n.every((v, i) => i === 0 || cmp(n[i - 1], v) <= 0) }).toBe(true)

  await header(page, 'Name').getByRole('button').click()
  await expect.poll(async () => { const n = await names(); return n.every((v, i) => i === 0 || cmp(n[i - 1], v) >= 0) }).toBe(true)
})

test('payments sort by amount on the server — page 1 ≥ page 2', async ({ page }) => {
  await page.getByRole('link', { name: 'Payments' }).click()
  await page.getByLabel('Rows').selectOption('10')
  const amountCol = 5 // Date, Customer, Plan, Method, Reference, Amount
  const amounts = async () => (await columnTexts(page, amountCol)).map(rupees)
  // The header and "Showing …" label update before the rows do, so wait for the server's answer
  const loaded = (match: RegExp) =>
    page.waitForResponse((r) => r.url().includes('/api/v1/payments/?') && match.test(r.url()))

  await header(page, 'Amount').getByRole('button').click()
  const sorted = loaded(/ordering=-amount/)
  await header(page, 'Amount').getByRole('button').click()
  await sorted
  await expect(header(page, 'Amount')).toHaveAttribute('aria-sort', 'descending')
  await expect(page.getByText(/^Showing 1–10 of/)).toBeVisible()

  await expect.poll(async () => { const a = await amounts(); return a.every((v, i) => i === 0 || a[i - 1] >= v) }).toBe(true)
  const page1 = await amounts()

  const page2Loaded = loaded(/[?&]page=2(&|$)/)
  await page.getByRole('button', { name: 'Next' }).click()
  await page2Loaded
  await expect(page.getByText(/^Showing 11–/)).toBeVisible()
  await expect.poll(async () => Math.max(...(await amounts()))).toBeLessThanOrEqual(Math.min(...page1))
  expect((await amounts()).length).toBeGreaterThan(0)
})

test('rows-per-page and paging never repeat a row', async ({ page }) => {
  await page.getByRole('link', { name: 'Customers' }).click()
  await page.getByLabel('Rows').selectOption('10')
  await header(page, 'Status').getByRole('button').click() // many ties → exercises the stable tie-breaker
  await expect(page.getByText(/^Showing 1–10 of/)).toBeVisible()
  const codes1 = await columnTexts(page, 0)
  await page.getByRole('button', { name: 'Next' }).click()
  await expect(page.getByText(/^Showing 11–/)).toBeVisible()
  const codes2 = await columnTexts(page, 0)
  expect(codes1).toHaveLength(10)
  expect(new Set([...codes1, ...codes2]).size).toBe(codes1.length + codes2.length)
})

test('changing sort jumps back to page 1', async ({ page }) => {
  await page.getByRole('link', { name: 'Customers' }).click()
  await page.getByLabel('Rows').selectOption('10')
  await page.getByRole('button', { name: 'Next' }).click()
  await expect(page.getByText(/^Showing 11–/)).toBeVisible()
  await header(page, 'Joined').getByRole('button').click()
  await expect(page.getByText(/^Showing 1–10 of/)).toBeVisible()
})

test('sorting combines with the status filter tabs', async ({ page }) => {
  await page.getByRole('link', { name: 'Subscriptions' }).click()
  await tab(page, 'Active').click()
  await header(page, 'Customer').getByRole('button').click()
  const statuses = await columnTexts(page, 2)
  expect(statuses.length).toBeGreaterThan(0)
  expect(new Set(statuses)).toEqual(new Set(['ACTIVE']))
})
