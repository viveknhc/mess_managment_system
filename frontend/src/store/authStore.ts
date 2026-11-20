import { create } from 'zustand'
import { apiClient, BUSINESS_SUSPENDED_EVENT, PAYMENT_REQUIRED_EVENT } from '../services/apiClient'
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
        await apiClient.post('/auth/logout/', { refresh })
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

// A request was rejected with PAYMENT_REQUIRED — the first MessDeck payment hasn't been made.
window.addEventListener(PAYMENT_REQUIRED_EVENT, () => {
  const { user } = useAuthStore.getState()
  if (user && user.saas_status !== 'PENDING') {
    useAuthStore.setState({ user: { ...user, saas_status: 'PENDING' } })
  }
})

/** Is the business locked out of everything except Billing/Support? */
export function businessLock(user: User | null): 'SUSPENDED' | 'PAYMENT_REQUIRED' | null {
  if (!user) return null
  if (user.business_status === 'SUSPENDED') return 'SUSPENDED'
  if (user.saas_status === 'PENDING') return 'PAYMENT_REQUIRED'
  return null
}
