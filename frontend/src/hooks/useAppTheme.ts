import { useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

/** Each role gets its own accent colour (see :root[data-theme] in index.css). */
const ROLE_THEME: Record<string, string> = {
  OWNER: 'owner',
  MANAGER: 'manager',
  DELIVERY_STAFF: 'delivery',
  KITCHEN_STAFF: 'kitchen',
  CUSTOMER: 'customer',
  SUPER_ADMIN: 'platform',
}

/** Routes drawn with the dark app theme. Landing and legal pages keep the light brand look. */
const APP_ROUTES = ['/app', '/platform', '/portal', '/staff', '/login', '/forgot-password', '/reset-password']

export function useAppTheme(): string | null {
  const { pathname } = useLocation()
  const role = useAuthStore((s) => s.user?.role)
  if (!APP_ROUTES.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return null
  return (role && ROLE_THEME[role]) || 'owner'
}
