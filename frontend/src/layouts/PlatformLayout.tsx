import { Outlet, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { type NavIconName } from '../components/ui/NavIcon'
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

  return (
    <AppShell
      title="Platform Management"
      subtitle="MessDeck"
      user={{ name: user?.name || user?.username || '', role: 'Platform admin' }}
      onLogout={handleLogout}
      nav={navItems}
    >
      <Outlet />
    </AppShell>
  )
}
