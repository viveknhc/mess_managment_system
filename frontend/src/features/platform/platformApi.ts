import { apiClient } from '../../services/apiClient'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// ── Types ────────────────────────────────────────────────────────────────

export interface SaasPlan {
  id: string
  name: string
  price_monthly: string
  max_customers: number
  max_staff: number
  features: string[]
}

export interface SaasSubscription {
  id: string
  business_id: string
  business_name: string
  plan: string | null
  plan_name: string | null
  plan_price: string | null
  status: 'TRIAL' | 'ACTIVE' | 'PAST_DUE' | 'SUSPENDED' | 'CANCELLED'
  trial_end_date: string | null
  current_period_start: string | null
  current_period_end: string | null
  days_remaining: number | null
}

export interface BillingData {
  subscription: SaasSubscription
  available_plans: SaasPlan[]
}

export interface PlatformBusiness {
  id: string
  name: string
  phone: string
  email: string
  status: string
  saas_status: string | null
  plan_name: string | null
  trial_end_date: string | null
  owner_name: string | null
  owner_email: string | null
  customer_count: number
  staff_count: number
  created_at: string
}

export interface SaasPayment {
  id: string
  business_id: string
  business_name: string
  plan_name: string | null
  amount: string
  status: string
  razorpay_payment_id: string
  period_start: string | null
  period_end: string | null
  failure_reason: string
  created_at: string
}

export interface PlatformStats {
  total_businesses: number
  active_businesses: number
  suspended_businesses: number
  trial_businesses: number
  paid_businesses: number
  total_revenue: string
  plans_breakdown: { plan__name: string; count: number }[]
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ── Helper ───────────────────────────────────────────────────────────────

function errMsg(e: unknown): string {
  if (axios.isAxiosError(e)) {
    return e.response?.data?.error?.message || e.message
  }
  return String(e)
}

// ── Public API (no auth required) ────────────────────────────────────────

export const publicApi = {
  async signup(data: {
    business_name: string
    owner_username: string
    owner_password: string
    owner_name?: string
    owner_email?: string
    owner_phone?: string
  }) {
    try {
      const res = await axios.post(`${API_BASE}/signup/`, data)
      return { ok: true as const, data: res.data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e) }
    }
  },

  async getPlans() {
    const { data } = await axios.get<SaasPlan[]>(`${API_BASE}/pricing/`)
    return data
  },
}

// ── Authenticated API ────────────────────────────────────────────────────

export const billingApi = {
  async getBilling() {
    const { data } = await apiClient.get<BillingData>('/billing/')
    return data
  },

  async checkout(planId: string) {
    try {
      const { data } = await apiClient.post('/billing/checkout/', { plan_id: planId })
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e) }
    }
  },
}

// ── Platform Admin API (SUPER_ADMIN) ─────────────────────────────────────

export const platformApi = {
  async getBusinesses(page = 1) {
    const { data } = await apiClient.get<PaginatedResponse<PlatformBusiness>>(
      `/platform/businesses/?page=${page}`,
    )
    return data
  },

  async suspendBusiness(id: string) {
    try {
      const { data } = await apiClient.post(`/platform/businesses/${id}/suspend/`)
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e) }
    }
  },

  async reactivateBusiness(id: string, extendTrialDays = 0) {
    try {
      const { data } = await apiClient.post(`/platform/businesses/${id}/reactivate/`, {
        extend_trial_days: extendTrialDays,
      })
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e) }
    }
  },

  async getPlans() {
    const { data } = await apiClient.get<PaginatedResponse<SaasPlan & { razorpay_plan_id: string; is_active: boolean }>>(
      '/platform/plans/',
    )
    return data
  },

  async createPlan(plan: Partial<SaasPlan & { razorpay_plan_id: string; is_active: boolean }>) {
    try {
      const { data } = await apiClient.post('/platform/plans/', plan)
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e) }
    }
  },

  async updatePlan(id: string, plan: Partial<SaasPlan & { razorpay_plan_id: string; is_active: boolean }>) {
    try {
      const { data } = await apiClient.patch(`/platform/plans/${id}/`, plan)
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e) }
    }
  },

  async deletePlan(id: string) {
    try {
      await apiClient.delete(`/platform/plans/${id}/`)
      return { ok: true as const }
    } catch (e) {
      return { ok: false as const, error: errMsg(e) }
    }
  },

  async getPayments(page = 1) {
    const { data } = await apiClient.get<PaginatedResponse<SaasPayment>>(
      `/platform/payments/?page=${page}`,
    )
    return data
  },

  async getStats() {
    const { data } = await apiClient.get<PlatformStats>('/platform/stats/')
    return data
  },
}
