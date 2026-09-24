import { create } from 'zustand'
import { apiClient } from '../services/apiClient'

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
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  fetchMe: () => Promise<void>
  reset: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,

  login: async (username, password) => {
    const { data } = await apiClient.post('/auth/login/', { username, password })
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    set({ user: data.user, isAuthenticated: true })
  },

  logout: async () => {
    const refresh = localStorage.getItem('refresh_token')
    try {
      if (refresh) {
        await apiClient.post('/auth/logout/', { refresh })
      }
    } catch {
      // Ignore errors during logout
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, isAuthenticated: false })
  },

  fetchMe: async () => {
    set({ isLoading: true })
    try {
      const { data } = await apiClient.get('/auth/me/')
      set({ user: data, isAuthenticated: true, isLoading: false })
    } catch {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      set({ user: null, isAuthenticated: false, isLoading: false })
    }
  },

  reset: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, isAuthenticated: false, isLoading: false })
  },
}))
