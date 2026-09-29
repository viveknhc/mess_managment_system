import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

const DELIVERY_NAV = [
  { to: '/staff', label: "Today's Deliveries", end: true },
  { to: '/staff/completed', label: 'Completed' },
]

const KITCHEN_NAV = [
  { to: '/staff', label: "Today's Meals", end: true },
  { to: '/staff/kitchen/summary', label: 'Summary' },
]

export function StaffLayout() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  const isKitchen = user?.role === 'KITCHEN_STAFF'
  const navItems = isKitchen ? KITCHEN_NAV : DELIVERY_NAV

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4">
          <h1 className="text-lg font-bold text-primary-600">{isKitchen ? 'Kitchen' : 'Delivery'}</h1>
          <button
            onClick={handleLogout}
            className="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100"
          >
            Logout
          </button>
        </div>
        <nav className="mx-auto max-w-3xl overflow-x-auto px-4">
          <div className="flex gap-1 pb-2">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                    isActive ? 'bg-primary-50 text-primary-700' : 'text-gray-600 hover:bg-gray-100'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>
      <main className="mx-auto w-full max-w-3xl flex-1 px-0 py-4 sm:px-4">
        <Outlet />
      </main>
    </div>
  )
}
