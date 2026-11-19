import { Outlet, NavLink, Navigate, Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { NotificationBell } from '../components/NotificationBell'
import { SUPPORT_EMAIL, supportEmailLink, whatsappLink } from '../config/support'
import { FEATURES, type FeatureKey } from '../hooks/useFeature'
import { NavIcon, type NavIconName } from '../components/ui/NavIcon'
import { AppShell } from '../components/AppShell'

const navItems: { to: string; label: string; icon: NavIconName; end: boolean; feature?: FeatureKey }[] = [
  { to: '/app', label: 'Dashboard', icon: 'dashboard', end: true },
  { to: '/app/customers', label: 'Customers', icon: 'users', end: false },
  { to: '/app/meals', label: 'Meals', icon: 'utensils', end: false },
  { to: '/app/plans', label: 'Plans', icon: 'clipboard', end: false },
  { to: '/app/subscriptions', label: 'Subscriptions', icon: 'calendarCheck', end: false },
  { to: '/app/payments', label: 'Customer Payments', icon: 'banknote', end: false },
  { to: '/app/deliveries', label: 'Deliveries', icon: 'truck', end: false },
  { to: '/app/reports', label: 'Reports', icon: 'chart', end: false, feature: FEATURES.REPORTS },
  { to: '/app/staff', label: 'Staff', icon: 'idBadge', end: false },
  { to: '/app/settings', label: 'Settings', icon: 'settings', end: false },
  { to: '/app/business', label: 'Business Profile', icon: 'store', end: false },
  { to: '/app/billing', label: 'MessDeck Billing', icon: 'creditCard', end: false },
  { to: '/app/support', label: 'Help & Support', icon: 'help', end: false },
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

  const logoutButton = (
    <button
      onClick={handleLogout}
      className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
    >
      Logout
    </button>
  )

  return (
    <AppShell
      brand={<h1 className="text-lg font-bold text-blue-600">Mess Manager</h1>}
      title={user?.business_name || 'Dashboard'}
      actions={
        <>
          {!suspended && <NotificationBell />}
          <span className="hidden text-sm text-gray-600 md:inline">
            {user?.name || user?.username}
            <span className="ml-1 rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700">
              {user?.role}
            </span>
          </span>
          <span className="hidden sm:inline">{logoutButton}</span>
        </>
      }
      drawerFooter={
        <div className="flex items-center justify-between gap-2">
          <span className="flex min-w-0 items-center gap-1 text-sm text-gray-600">
            <span className="truncate">{user?.name || user?.username}</span>
            <span className="shrink-0 rounded bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-700">{user?.role}</span>
          </span>
          {logoutButton}
        </div>
      }
      nav={navItems.filter((item) => !item.feature || user?.features?.includes(item.feature)).map((item) =>
        suspended && !SUSPENDED_ALLOWED.includes(item.to) ? (
          // Blocked while suspended — shown greyed out instead of a link that bounces back to Billing.
          <span
            key={item.to}
            title="Unavailable while your account is suspended"
            aria-disabled="true"
            className="flex cursor-not-allowed items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-300"
          >
            <NavIcon name={item.icon} />
            {item.label}
          </span>
        ) : (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
                isActive
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <NavIcon name={item.icon} />
            {item.label}
          </NavLink>
        ),
      )}
    >
      {suspended && (
        <div role="alert" className="border-b border-red-200 bg-red-50 px-4 py-3 text-center text-sm font-medium text-red-700 sm:px-6">
          Your business account is suspended. Please{' '}
          <Link to="/app/billing#pay" className="underline">
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
          <a href={supportEmailLink('MessDeck account suspended')} className="break-all underline">
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
    </AppShell>
  )
}
