import { create } from 'zustand'
import { apiClient, BUSINESS_SUSPENDED_EVENT, PAYMENT_REQUIRED_EVENT, revokeRefreshToken } from '../services/apiClient'
import { tokenStorage } from '../services/tokenStorage'

export interface User {
  id: string
  username: string
  name: string
  email: string
  phone: string
  role: string
  is_active: boolean
  business_id: string | null
  business_name: string | null
  business_status: string | null
  /** MessDeck billing status. PENDING = first payment not made yet → app locked except Billing/Support. */
  saas_status: string | null
  /** End of the free trial (ISO datetime) while saas_status is TRIAL — past it the app locks until the first payment. */
  trial_ends_at: string | null
  /** Feature keys the business has (backend customization.registry) — see useFeature(). */
  features: string[]
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  fetchMe: () => Promise<void>
  /** Re-read /auth/me/ without a loading state — e.g. after paying, to unlock the app. */
  refreshUser: () => Promise<void>
  reset: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!tokenStorage.getAccess(),
  isLoading: false,

  login: async (username, password) => {
    const { data } = await apiClient.post('/auth/login/', { username, password })
    tokenStorage.setTokens(data.access, data.refresh)
    set({ user: data.user, isAuthenticated: true })
  },

  logout: async () => {
    const refresh = tokenStorage.getRefresh()
    try {
      if (refresh) {
        await revokeRefreshToken(refresh)
      }
    } catch {
      // Ignore errors during logout
    }
    tokenStorage.clear()
    set({ user: null, isAuthenticated: false })
  },

  fetchMe: async () => {
    set({ isLoading: true })
    try {
      const { data } = await apiClient.get('/auth/me/')
      set({ user: data, isAuthenticated: true, isLoading: false })
    } catch {
      tokenStorage.clear()
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },

  refreshUser: async () => {
    try {
      const { data } = await apiClient.get('/auth/me/')
      set({ user: data })
    } catch {
      // Keep the current user — a failed refresh shouldn't log anyone out.
    }
  },

  reset: () => {
    tokenStorage.clear()
    set({ user: null, isAuthenticated: false, isLoading: false })
  },
}))

// A request was rejected with BUSINESS_SUSPENDED — the business was suspended mid-session.
window.addEventListener(BUSINESS_SUSPENDED_EVENT, () => {
  const { user } = useAuthStore.getState()
  if (user && user.business_status !== 'SUSPENDED') {
    useAuthStore.setState({ user: { ...user, business_status: 'SUSPENDED' } })
  }
})

// A request was rejected with PAYMENT_REQUIRED — first MessDeck payment not made (or the free trial ran out).
window.addEventListener(PAYMENT_REQUIRED_EVENT, () => {
  const { user } = useAuthStore.getState()
  if (!user || businessLock(user) === 'PAYMENT_REQUIRED') return
  if (user.saas_status === 'TRIAL') {
    useAuthStore.setState({ user: { ...user, trial_ends_at: new Date().toISOString() } })
  } else {
    useAuthStore.setState({ user: { ...user, saas_status: 'PENDING' } })
  }
})

/** Milliseconds left in a running free trial; null when there's no trial, ≤ 0 once it has ended. */
export function trialMsLeft(user: User | null, now = Date.now()): number | null {
  if (!user || user.saas_status !== 'TRIAL' || !user.trial_ends_at) return null
  return Date.parse(user.trial_ends_at) - now
}

/** Did the business's free trial run out (app locked until the first payment)? */
export function trialEnded(user: User | null, now = Date.now()) {
  const left = trialMsLeft(user, now)
  return left !== null && left <= 0
}

/** Is the business locked out of everything except Billing/Support? */
export function businessLock(user: User | null, now = Date.now()): 'SUSPENDED' | 'PAYMENT_REQUIRED' | null {
  if (!user) return null
  if (user.business_status === 'SUSPENDED') return 'SUSPENDED'
  if (user.saas_status === 'PENDING' || trialEnded(user, now)) return 'PAYMENT_REQUIRED'
  return null
}
