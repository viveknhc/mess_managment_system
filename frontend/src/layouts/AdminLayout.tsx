import { Outlet, NavLink, Navigate, Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { NotificationBell } from '../components/NotificationBell'
import { SUPPORT_EMAIL, supportEmailLink, whatsappLink } from '../config/support'

const navItems = [
  { to: '/app', label: 'Dashboard', end: true },
  { to: '/app/customers', label: 'Customers', end: false },
  { to: '/app/meals', label: 'Meals', end: false },
  { to: '/app/plans', label: 'Plans', end: false },
  { to: '/app/subscriptions', label: 'Subscriptions', end: false },
  { to: '/app/payments', label: 'Customer Payments', end: false },
  { to: '/app/deliveries', label: 'Deliveries', end: false },
  { to: '/app/reports', label: 'Reports', end: false },
  { to: '/app/staff', label: 'Staff', end: false },
  { to: '/app/settings', label: 'Settings', end: false },
  { to: '/app/business', label: 'Business Profile', end: false },
  { to: '/app/billing', label: 'MessDeck Billing', end: false },
  { to: '/app/support', label: 'Help & Support', end: false },
]

/** Pages a suspended business can still use — the backend allows /auth/* and /billing/* only. */
const SUSPENDED_ALLOWED = ['/app/billing', '/app/support']

export function AdminLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const suspended = user?.business_status === 'SUSPENDED'

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-64 border-r border-gray-200 bg-white">
        <div className="flex h-16 items-center border-b border-gray-200 px-6">
          <h1 className="text-lg font-bold text-blue-600">Mess Manager</h1>
        </div>
        <nav className="space-y-1 p-4">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
          <h2 className="text-lg font-semibold text-gray-800">
            {user?.business_name || 'Dashboard'}
          </h2>
          <div className="flex items-center gap-4">
            <NotificationBell />
            <span className="text-sm text-gray-600">
              {user?.name || user?.username}
              <span className="ml-1 rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700">
                {user?.role}
              </span>
            </span>
            <button
              onClick={handleLogout}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
            >
              Logout
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto bg-gray-50">
          {suspended && (
            <div role="alert" className="border-b border-red-200 bg-red-50 px-6 py-3 text-center text-sm font-medium text-red-700">
              Your business account is suspended. Please{' '}
              <Link to="/app/billing" className="underline">
                pay the amount due
              </Link>{' '}
              or contact support on{' '}
              <a
                href={whatsappLink(`Hi, my MessDeck account for ${user?.business_name ?? 'my business'} is suspended.`)}
                target="_blank"
                rel="noopener noreferrer"
                className="underline"
              >
                WhatsApp
              </a>{' '}
              or{' '}
              <a href={supportEmailLink('MessDeck account suspended')} className="underline">
                {SUPPORT_EMAIL}
              </a>{' '}
              to reactivate.
            </div>
          )}
          {suspended && !SUSPENDED_ALLOWED.some((p) => pathname.startsWith(p)) ? (
            <Navigate to="/app/billing" replace />
          ) : (
            <Outlet />
          )}
        </main>
      </div>
    </div>
  )
}
