import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { NavIcon, type NavIconName } from '../components/ui/NavIcon'
import { AppShell } from '../components/AppShell'

const navItems: { to: string; label: string; icon: NavIconName; end: boolean }[] = [
  { to: '/platform', label: 'Dashboard', icon: 'dashboard', end: true },
  { to: '/platform/businesses', label: 'Businesses', icon: 'building', end: false },
  { to: '/platform/messes', label: 'Mess Details', icon: 'soup', end: false },
  { to: '/platform/plans', label: 'Plans', icon: 'package', end: false },
  { to: '/platform/payments', label: 'Payments', icon: 'creditCard', end: false },
]

export function PlatformLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const userBadge = (
    <span className="text-sm text-gray-600">
      {user?.name || user?.username}
      <span className="ml-1 rounded bg-purple-100 px-1.5 py-0.5 text-xs font-medium text-purple-700">
        SUPER_ADMIN
      </span>
    </span>
  )
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
      brand={<h1 className="text-lg font-bold text-purple-600">Platform Admin</h1>}
      title="Platform Management"
      actions={
        <>
          <span className="hidden md:inline">{userBadge}</span>
          <span className="hidden sm:inline">{logoutButton}</span>
        </>
      }
      drawerFooter={
        <div className="flex flex-wrap items-center justify-between gap-2">
          {userBadge}
          {logoutButton}
        </div>
      }
      nav={navItems.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
              isActive
                ? 'bg-purple-50 text-purple-700'
                : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }`
          }
        >
          <NavIcon name={item.icon} />
          {item.label}
        </NavLink>
      ))}
    >
      <Outlet />
    </AppShell>
  )
}
