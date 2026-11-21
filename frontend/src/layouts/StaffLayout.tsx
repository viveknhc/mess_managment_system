import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { businessLock, useAuthStore } from '../store/authStore'
import { SuspendedNotice } from '../components/SuspendedNotice'
import { KitchenClosedNotice } from '../components/KitchenClosedNotice'
import { NavIcon, type NavIconName } from '../components/ui/NavIcon'

// Delivery staff have one screen (To deliver / Done tabs inside it), so no nav for them.
const KITCHEN_NAV: { to: string; label: string; icon: NavIconName; end?: boolean }[] = [
  { to: '/staff', label: "Today's Meals", icon: 'chefHat', end: true },
  { to: '/staff/kitchen/summary', label: 'Summary', icon: 'clipboard' },
]

export function StaffLayout() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  const isKitchen = user?.role === 'KITCHEN_STAFF'
  const firstName = (user?.name || user?.username || '').split(' ')[0]

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex h-16 max-w-2xl items-center justify-between gap-3 px-4">
          <div className="flex min-w-0 items-center gap-3">
            <div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-100 text-base font-bold text-primary-700"
              aria-hidden="true"
            >
              {firstName.charAt(0).toUpperCase() || '?'}
            </div>
            <div className="min-w-0">
              <p className="truncate text-base font-semibold text-gray-900">Hi, {firstName}</p>
              <p className="truncate text-xs text-gray-500">
                {user?.business_name} · {isKitchen ? 'Kitchen' : 'Delivery'}
              </p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="shrink-0 rounded-xl border border-gray-200 px-3 py-2 text-sm font-medium text-gray-600 active:bg-gray-100"
          >
            Logout
          </button>
        </div>
        {isKitchen && (
          <nav className="mx-auto max-w-2xl overflow-x-auto px-4">
            <div className="flex gap-1 pb-2">
              {KITCHEN_NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                      isActive ? 'bg-primary-50 text-primary-700' : 'text-gray-600 hover:bg-gray-100'
                    }`
                  }
                >
                  <NavIcon name={item.icon} className="h-4 w-4 shrink-0" />
                  {item.label}
                </NavLink>
              ))}
            </div>
          </nav>
        )}
      </header>
      {!businessLock(user) && <KitchenClosedNotice />}
      <main className="mx-auto w-full max-w-2xl flex-1 py-4">
        {businessLock(user) ? <SuspendedNotice /> : <Outlet />}
      </main>
    </div>
  )
}
