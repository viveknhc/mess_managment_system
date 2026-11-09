import { apiClient } from '../../services/apiClient'
import { getApiErrorMessage } from '../../utils/apiError'

// ── Types ────────────────────────────────────────────────────────────────

export interface SaasPlan {
  id: string
  name: string
  price_monthly: string
  setup_fee: string
  reactivation_fee: string
  max_customers: number
  max_staff: number
  features: string[]
}

export type SaasStatus = 'PENDING' | 'TRIAL' | 'ACTIVE' | 'PAST_DUE' | 'SUSPENDED' | 'CANCELLED'

export interface AmountDue {
  setup_fee: string
  reactivation_fee: string
  monthly_fee: string
  total: string
  due_date: string
}

export interface SaasSubscription {
  id: string
  business_id: string
  business_name: string
  business_status: string
  plan: string | null
  plan_name: string | null
  plan_price: string | null
  plan_details: SaasPlan | null
  status: SaasStatus
  setup_fee_paid: boolean
  cancelled_at: string | null
  trial_end_date: string | null
  current_period_start: string | null
  /** First day not covered by the last payment — the next fee is due on this date. */
  current_period_end: string | null
  days_remaining: number | null
  grace_ends: string | null
  amount_due: AmountDue
}

export interface BillingData {
  subscription: SaasSubscription
  payments: SaasPayment[]
}

export type ManualPaymentMethod = 'UPI' | 'CASH' | 'BANK_TRANSFER'

export interface CreateBusinessInput {
  business_name: string
  phone?: string
  email?: string
  address?: string
  owner_username: string
  owner_password: string
  owner_name?: string
  owner_email?: string
  owner_phone?: string
}

export interface PlatformBusiness {
  id: string
  name: string
  phone: string
  email: string
  status: string
  saas_status: SaasStatus | null
  plan_name: string | null
  trial_end_date: string | null
  paid_until: string | null
  amount_due: AmountDue | null
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
  setup_fee: string
  reactivation_fee: string
  status: string
  method: string
  reference: string
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
  pending_businesses: number
  past_due_businesses: number
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
  return getApiErrorMessage(e, String(e))
}

// ── Authenticated API ────────────────────────────────────────────────────

export const billingApi = {
  async getBilling() {
    const { data } = await apiClient.get<BillingData>('/billing/')
    return data
  },

  async cancel() {
    try {
      const { data } = await apiClient.post<{ subscription: SaasSubscription }>('/billing/cancel/')
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e) }
    }
  },
}

// ── Platform Admin API (SUPER_ADMIN) ─────────────────────────────────────

export const platformApi = {
  async getBusinesses(params: Record<string, string> = {}) {
    const { data } = await apiClient.get<PaginatedResponse<PlatformBusiness>>('/platform/businesses/', { params })
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

  async reactivateBusiness(id: string) {
    try {
      const { data } = await apiClient.post(`/platform/businesses/${id}/reactivate/`)
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e) }
    }
  },

  async createBusiness(input: CreateBusinessInput) {
    try {
      const { data } = await apiClient.post<PlatformBusiness>('/platform/businesses/', input)
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e) }
    }
  },

  async recordPayment(id: string, payment: { amount: string; method: ManualPaymentMethod; reference?: string }) {
    try {
      const { data } = await apiClient.post<SaasPayment>(`/platform/businesses/${id}/record-payment/`, payment)
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e) }
    }
  },

  async cancelBusiness(id: string) {
    try {
      const { data } = await apiClient.post(`/platform/businesses/${id}/cancel/`)
      return { ok: true as const, data }
    } catch (e) {
      return { ok: false as const, error: errMsg(e) }
    }
  },

  async getPlans(params: Record<string, string> = {}) {
    const { data } = await apiClient.get<PaginatedResponse<SaasPlan & { razorpay_plan_id: string; is_active: boolean }>>(
      '/platform/plans/',
      { params },
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

  async getPayments(params: Record<string, string> = {}) {
    const { data } = await apiClient.get<PaginatedResponse<SaasPayment>>('/platform/payments/', { params })
    return data
  },

  async getStats() {
    const { data } = await apiClient.get<PlatformStats>('/platform/stats/')
    return data
  },
}
