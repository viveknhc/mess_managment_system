import { Outlet, Navigate, Link, useLocation, useNavigate } from 'react-router-dom'
import { useCallback, useState } from 'react'
import { businessLock, trialEnded, useAuthStore } from '../store/authStore'
import { NotificationBell } from '../components/NotificationBell'
import { SUPPORT_EMAIL, supportEmailLink, whatsappLink } from '../config/support'
import { FEATURES, type FeatureKey } from '../hooks/useFeature'
import { type NavIconName } from '../components/ui/NavIcon'
import { AppShell } from '../components/AppShell'
import { TrialCountdownBanner } from '../components/TrialCountdownBanner'
import { KitchenClosedNotice } from '../components/KitchenClosedNotice'

const navItems: { to: string; label: string; icon: NavIconName; end: boolean; feature?: FeatureKey }[] = [
  { to: '/app', label: 'Dashboard', icon: 'dashboard', end: true },
  { to: '/app/customers', label: 'Customers', icon: 'users', end: false },
  { to: '/app/meals', label: 'Meals', icon: 'utensils', end: false },
  { to: '/app/plans', label: 'Plans', icon: 'clipboard', end: false },
  { to: '/app/subscriptions', label: 'Subscriptions', icon: 'calendarCheck', end: false },
  { to: '/app/payments', label: 'Customer Payments', icon: 'banknote', end: false },
  { to: '/app/deliveries', label: 'Deliveries', icon: 'truck', end: false },
  { to: '/app/routes', label: 'Delivery Routes', icon: 'route', end: false, feature: FEATURES.DELIVERY_ROUTES },
  { to: '/app/reports', label: 'Reports', icon: 'chart', end: false, feature: FEATURES.REPORTS },
  { to: '/app/staff', label: 'Staff', icon: 'idBadge', end: false },
  { to: '/app/settings', label: 'Settings', icon: 'settings', end: false },
  { to: '/app/business', label: 'Business Profile', icon: 'store', end: false },
  { to: '/app/billing', label: 'MessDeck Billing', icon: 'creditCard', end: false },
  { to: '/app/support', label: 'Help & Support', icon: 'help', end: false },
]

const ROLE_LABELS: Record<string, string> = { OWNER: 'Owner', MANAGER: 'Manager' }

/** Pages a locked business (suspended, or first payment not made) can still use — the backend allows /auth/* and /billing/* only. */
const SUSPENDED_ALLOWED = ['/app/billing', '/app/support']

export function AdminLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  // Bumped when the trial countdown hits zero so the lock below is re-evaluated against the new time.
  const [, setTrialTick] = useState(0)
  const onTrialEnd = useCallback(() => setTrialTick((n) => n + 1), [])
  const lock = businessLock(user)
  const suspended = lock !== null
  const trialOver = trialEnded(user)

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const lockedReason =
    lock === 'PAYMENT_REQUIRED'
      ? trialOver ? 'Free trial ended — available after your first payment' : 'Available after your first payment'
      : 'Unavailable while your account is suspended'

  return (
    <AppShell
      title={user?.business_name || 'Dashboard'}
      user={{ name: user?.name || user?.username || '', role: ROLE_LABELS[user?.role ?? ''] ?? user?.role ?? '' }}
      onLogout={handleLogout}
      actions={!suspended && <NotificationBell />}
      nav={navItems
        .filter((item) => !item.feature || user?.features?.includes(item.feature))
        .map((item) => ({
          ...item,
          // Blocked while locked — shown greyed out instead of a link that bounces back to Billing.
          disabledReason: suspended && !SUSPENDED_ALLOWED.includes(item.to) ? lockedReason : undefined,
        }))}
    >
      {!lock && <KitchenClosedNotice />}
      {!suspended && user?.saas_status === 'TRIAL' && user.trial_ends_at && (
        <TrialCountdownBanner endsAt={user.trial_ends_at} onEnd={onTrialEnd} />
      )}
      {lock === 'PAYMENT_REQUIRED' && (
        <div role="alert" className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-center text-sm font-medium text-amber-800 sm:px-6">
          {trialOver ? (
            <>
              Your 7-day free trial has ended. Your data is safe —{' '}
              <Link to="/app/billing#pay" className="underline">
                complete your first payment
              </Link>{' '}
              to continue using MessDeck
            </>
          ) : (
            <>
              Welcome to MessDeck! To start adding customers, meals and plans,{' '}
              <Link to="/app/billing#pay" className="underline">
                complete your first payment
              </Link>
            </>
          )}
          . Need help? Message us on{' '}
          <a
            href={whatsappLink(`Hi, I need help with the first payment for ${user?.business_name ?? 'my business'} on MessDeck.`)}
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
          >
            WhatsApp
          </a>
          .
        </div>
      )}
      {lock === 'SUSPENDED' && (
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
