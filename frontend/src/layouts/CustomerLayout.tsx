import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { businessLock, useAuthStore } from '../store/authStore'
import { SuspendedNotice } from '../components/SuspendedNotice'
import { KitchenClosedNotice } from '../components/KitchenClosedNotice'
import { FeatureGate } from '../components/FeatureGate'
import { FEATURES } from '../hooks/useFeature'
import { NavIcon, type NavIconName } from '../components/ui/NavIcon'

const NAV_ITEMS: { to: string; label: string; icon: NavIconName; end?: boolean }[] = [
  { to: '/portal', label: 'Dashboard', icon: 'dashboard', end: true },
  { to: '/portal/subscription', label: 'My Subscription', icon: 'calendarCheck' },
  { to: '/portal/meals', label: 'My Meals', icon: 'utensils' },
  { to: '/portal/payments', label: 'Payments', icon: 'banknote' },
  { to: '/portal/profile', label: 'Profile', icon: 'user' },
]

export function CustomerLayout() {
  const navigate = useNavigate()
  const logout = useAuthStore((s) => s.logout)
  const suspended = useAuthStore((s) => businessLock(s.user) !== null)

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
      </header>
      {!suspended && <KitchenClosedNotice />}
      <main className="mx-auto w-full max-w-3xl flex-1 px-0 py-4 sm:px-4">
        {suspended ? (
          <SuspendedNotice />
        ) : (
          <FeatureGate
            feature={FEATURES.CUSTOMER_PORTAL}
            message="Online access isn't available for your mess. Please contact your mess directly."
          >
            <Outlet />
          </FeatureGate>
        )}
      </main>
      <footer className="border-t border-gray-200 bg-white py-3 text-center text-xs text-gray-400">
        Powered by Mess Management
      </footer>
    </div>
  )
}
