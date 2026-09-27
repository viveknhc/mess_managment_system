import { create } from 'zustand'
import { apiClient } from '../services/apiClient'

export interface Business {
  id: string
  name: string
  phone: string
  email: string
  address: string
  logo: string | null
  status: string
  created_at: string
  updated_at: string
}

interface BusinessState {
  business: Business | null
  isLoading: boolean
  error: string | null
  fetchBusiness: () => Promise<void>
  updateBusiness: (data: Partial<Business>) => Promise<void>
  uploadLogo: (file: File) => Promise<void>
  reset: () => void
}

export const useBusinessStore = create<BusinessState>((set, get) => ({
  business: null,
  isLoading: false,
  error: null,

  fetchBusiness: async () => {
    set({ isLoading: true, error: null })
    try {
      const { data } = await apiClient.get('/business/')
      const biz = data.results?.[0] ?? null
      set({ business: biz, isLoading: false })
    } catch {
      set({ error: 'Failed to load business profile', isLoading: false })
    }
  },

  updateBusiness: async (updates) => {
    const biz = get().business
    if (!biz) return
    set({ isLoading: true, error: null })
    try {
      const { data } = await apiClient.patch(`/business/${biz.id}/`, updates)
      set({ business: data, isLoading: false })
    } catch {
      set({ error: 'Failed to update business profile', isLoading: false })
    }
  },

  uploadLogo: async (file) => {
    const biz = get().business
    if (!biz) return
    set({ isLoading: true, error: null })
    try {
      const formData = new FormData()
      formData.append('logo', file)
      const { data } = await apiClient.patch(`/business/${biz.id}/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      set({ business: data, isLoading: false })
    } catch {
      set({ error: 'Failed to upload logo', isLoading: false })
    }
  },

  reset: () => set({ business: null, isLoading: false, error: null }),
}))
