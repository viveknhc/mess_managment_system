import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

const NAV_ITEMS = [
  { to: '/portal', label: 'Dashboard', end: true },
  { to: '/portal/subscription', label: 'My Subscription' },
  { to: '/portal/meals', label: 'My Meals' },
  { to: '/portal/payments', label: 'Payments' },
  { to: '/portal/profile', label: 'Profile' },
]

export function CustomerLayout() {
  const navigate = useNavigate()
  const logout = useAuthStore((s) => s.logout)

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4">
          <h1 className="text-lg font-bold text-primary-600">My Mess</h1>
          <button
            onClick={handleLogout}
            className="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-100"
          >
            Logout
          </button>
        </div>
        <nav className="mx-auto max-w-3xl overflow-x-auto px-4">
          <div className="flex gap-1 pb-2">
            {NAV_ITEMS.map((item) => (
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
      <footer className="border-t border-gray-200 bg-white py-3 text-center text-xs text-gray-400">
        Powered by Mess Management
      </footer>
    </div>
  )
}
