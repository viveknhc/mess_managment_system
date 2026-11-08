import { expect, test } from '@playwright/test'
import { USERS, login, logout } from './helpers'

test.describe('Login & role routing', () => {
  for (const key of ['superadmin', 'owner', 'manager', 'delivery', 'customer1'] as const) {
    const user = USERS[key]
    test(`${key} lands on ${user.home}`, async ({ page }) => {
      await login(page, user, user.home)
      await logout(page)
    })
  }

  test('kitchen staff lands on /staff', async ({ page }) => {
    await login(page, USERS.kitchen, USERS.kitchen.home)
    await expect(page.getByRole('heading', { name: "Today's Meals" })).toBeVisible()
    await logout(page)
  })

  test('wrong password shows an error and stays on login', async ({ page }) => {
    await login(page, { username: 'owner', password: 'wrong-password' })
    await expect(page.getByText('Invalid username or password')).toBeVisible()
    await expect(page).toHaveURL(/\/login$/)
  })

  test('logged-out user is sent to login', async ({ page }) => {
    await page.goto('/app/payments')
    await expect(page).toHaveURL(/\/login$/)
  })

  test('customer cannot open owner pages', async ({ page }) => {
    await login(page, USERS.customer3, '/portal')
    await page.goto('/app/customers')
    await expect(page).toHaveURL(/\/portal$/)
  })

  test('delivery staff cannot open owner pages', async ({ page }) => {
    await login(page, USERS.delivery, '/staff')
    await page.goto('/app/payments')
    await expect(page).toHaveURL(/\/staff$/)
  })

  test('each tab keeps its own login', async ({ context }) => {
    const ownerTab = await context.newPage()
    await login(ownerTab, USERS.owner, '/app')
    const customerTab = await context.newPage()
    await login(customerTab, USERS.customer3, '/portal')
    await ownerTab.reload()
    await expect(ownerTab).toHaveURL(/\/app$/)
    await expect(ownerTab.getByText('OWNER', { exact: true })).toBeVisible()
    await customerTab.reload()
    await expect(customerTab).toHaveURL(/\/portal$/)
  })
})
